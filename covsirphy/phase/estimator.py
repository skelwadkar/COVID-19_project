#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import optuna
import pandas as pd
from covsirphy.analysis.simulator import ODESimulator
from covsirphy.ode.mbase import ModelBase
from covsirphy.phase.ode_data import ODEData
from covsirphy.phase.optimize import Optimizer
from covsirphy.util.stopwatch import StopWatch


class Estimator(Optimizer):
    """
    Hyperparameter optimization of an ODE model.
    """
    np.seterr(divide="raise")

    def __init__(self, clean_df, model, population,
                 country, province=None,
                 start_date=None, end_date=None, **kwargs):
        """
        @clean_df <pd.DataFrame>:
            - cleaned observed data or simulated data
            - observed data
                - index <int>: reset index
                - Date <pd.TimeStamp>: Observation date
                - Country <str>: country/region name
                - Province <str>: province/prefecture/sstate name
                - Confirmed <int>: the number of confirmed cases
                - Infected <int>: the number of currently infected cases
                - Fatal <int>: the number of fatal cases
                - Recovered <int>: the number of recovered cases
            - simulated data
                - index <int>: reset index
                - Date <pd.TimeStamp>: Observation date
                - Country <str>: country/region name
                - Province <str>: province/prefecture/state name
                - variables of the models <int>
        @model <subclass of cs.ModelBase>: ODE model
        @population <int>: total population in the place
        @country <str>: country name
        @province <str>: province name
        @start_date <str>: start date, like 22Jan2020
        @end_date <str>: end date, like 01Feb2020
        @kwargs: parameter values of the model
        """
        # Read arguments
        model = self.validate_subclass(model, ModelBase, name="model")
        self.model = model
        self.population = population
        self.country = country
        self.province = province
        self.start_date = start_date
        self.end_date = end_date
        self.fixed_dict = kwargs.copy()
        if self.TAU in self.fixed_dict.keys():
            self.fixed_dict[self.TAU] = self.validate_natural_int(
                self.fixed_dict[self.TAU], name="tau"
            )
        # Training dataset
        df = self.validate_dataframe(
            clean_df, name="clean_df", columns=model.VARIABLES
        )
        if set(self.VALUE_COLUMNS) not in set(df.columns):
            df = model.restore(df)
        self.ode_data = ODEData(df, country=country, province=province)
        self.y0_dict = self.ode_data.y0(model, population, start_date=start_date)
        # For optimization
        optuna.logging.disable_default_handler()
        self.x = self.TS
        self.y_list = model.VARIABLES[:]
        self.study = None
        self.total_trials = 0
        self.run_time = 0
        self.tau_candidates = self.divisors(1440)
        # Defined in parent class, but not used
        self.train_df = None
        # step_n will be defined in divide_minutes()
        self.step_n = None

    def _run_trial(self, n_jobs, timeout_iteration):
        """
        Run trial.
        @n_jobs <int>: the number of parallel jobs or -1 (CPU count)
        @timeout_iteration <int>: time-out of one iteration
        """
        self.study.optimize(
            lambda x: self.objective(x),
            n_jobs=n_jobs,
            timeout=timeout_iteration
        )

    def run(self, timeout=60, n_jobs=-1, reset_n_max=3,
            timeout_iteration=10, allowance=(0.8, 1.2)):
        """
        Run optimization.
        If the result satisfied all conditions, optimization ends.
            - all values are not under than 0
            - values of monotonic increasing variables increases monotonically
            - predicted values are in the allowance
                when each actual value shows max value
        - @timeout <int>: time-out of run
        @n_jobs <int>: the number of parallel jobs or -1 (CPU count)
        @reset_n_max <int>:
            - if study was reset @reset_n_max times, will not be reset anymore
        @timeout_iteration <int>: time-out of one iteration
        @allowance <tuple(float, float)>:
            - the allowance of the predicted value
        @return None
        """
        if self.study is None:
            self._init_study()
        print("\tRunning optimization...")
        stopwatch = StopWatch()
        reset_n = 0
        while True:
            # Perform optimization
            self._run_trial(n_jobs=n_jobs, timeout_iteration=timeout_iteration)
            self.run_time = stopwatch.stop()
            self.total_trials = len(self.study.trials)
            # Time-out
            if self.run_time >= timeout:
                break
            print(
                f"\r\tPerformed {self.total_trials} trials in {stopwatch.show()}.",
                end=str()
            )
            # Create a table to compare observed/estimated values
            tau = super().param()[self.TAU]
            train_df = self.divide_minutes(tau)
            comp_df = self.compare(train_df, self.predict())
            # Check monotonic variables
            mono_ok_list = [
                comp_df[f"{v}{self.P}"].is_monotonic_increasing
                for v in self.model.VARS_INCLEASE
            ]
            if not all(mono_ok_list):
                reset_n += 1
                if reset_n <= reset_n_max:
                    # Initialize the study
                    self._init_study()
                    stopwatch = StopWatch()
                    continue
            # Check the values when argmax(actual)
            values_nest = [
                comp_df.loc[
                    comp_df[f"{v}{self.A}"].idxmax(),
                    [f"{v}{self.A}", f"{v}{self.P}"]
                ].tolist()
                for v in self.model.VARIABLES
            ]
            last_ok_list = [
                (a * allowance[0] <= p) and (p <= a * allowance[1])
                for (a, p) in values_nest
            ]
            if not all(last_ok_list):
                continue
            break
        stopwatch.stop()
        print(
            f"\r\tFinished {self.total_trials} trials in {stopwatch.show()}.\n",
            end=str()
        )
        return None

    def objective(self, trial):
        """
        Objective function of Optuna study.
        This defines the parameter values using Optuna.
        @trial <optuna.trial>: a trial of the study
        @return <float>: score of the error function to minimize
        """
        fixed_dict = self.fixed_dict.copy()
        # Convert T to t using tau
        if self.TAU in fixed_dict.keys():
            tau = fixed_dict.pop(self.TAU)
        else:
            tau = trial.suggest_categorical(self.TAU, self.tau_candidates)
        tau = self.validate_natural_int(tau, name=self.TAU)
        taufree_df = self.divide_minutes(tau)
        # Set parameters of the models
        model_param_dict = self.model.param_range(
            taufree_df, self.population
        )
        p_dict = {
            k: trial.suggest_uniform(k, *v)
            for (k, v) in model_param_dict.items()
            if k not in self.fixed_dict.keys()
        }
        p_dict.update(fixed_dict)
        return self.error_f(p_dict, taufree_df)

    def divide_minutes(self, tau):
        """
        Divide T by tau in the training dataset.
        @tau <int>: tau value [min]
        @return <pd.DataFrame>:
            - index: reset index
            - t <int>: Elapsed time divided by tau value [-]
            - columns with dimensional variables
        """
        tau = self.validate_natural_int(tau, name="tau")
        taufree_df = self.ode_data.make(
            model=self.model,
            population=self.population,
            start_date=self.start_date,
            end_date=self.end_date,
            tau=tau
        )
        self.step_n = int(taufree_df[self.TS].max())
        return taufree_df

    def error_f(self, param_dict, taufree_df):
        """
        Definition of error score to minimize in the study.
        @param_dict <dict[str]=int/float>:
            - estimated parameter values
        @taufree_df <pd.DataFrame>: training dataset
            - index: reset index
            - t: time steps [-]
            - columns with dimensional variables
        @return <float>: score of the error function to minimize
        """
        if self.step_n is None:
            raise ValueError("self.step_n must be defined in advance.")
        sim_df = self.simulate(self.step_n, param_dict)
        df = self.compare(taufree_df, sim_df)
        # Calculate error score
        v_list = [
            v for (p, v)
            in zip(self.model.PRIORITIES, self.model.VARIABLES)
            if p > 0
        ]
        diffs = [df[f"{v}{self.A}"] - df[f"{v}{self.P}"] for v in v_list]
        numerators = [df[f"{v}{self.A}"] + 1 for v in v_list]
        try:
            scores = [
                p * np.average(diff.abs() / numerator, weights=df.index)
                for (p, diff, numerator)
                in zip(self.model.PRIORITIES, diffs, numerators)
            ]
        except ZeroDivisionError:
            return np.inf
        return sum(scores)

    def simulate(self, step_n, param_dict):
        """
        Simulate the values with the parameters.
        @step_n <int>: number of iteration
        @param_dict <dict[str]=int/float>:
            - estimated parameter values
        @return <pd.DataFrame>:
            - index: reset index
            - t <int>: Elapsed time divided by tau value [-]
            - columns with dimensionalized variables
        """
        simulator = ODESimulator(country=self.country, province=self.province)
        simulator.add(
            model=self.model,
            step_n=step_n,
            population=self.population,
            param_dict=param_dict,
            y0_dict=self.y0_dict
        )
        simulator.run()
        return simulator.taufree()

    def summary(self, name):
        """
        Summarize the results of optimization.
        This function should be overwritten in subclass.
        @name <str>: index of the dataframe
        @return <pd.DataFrame>:
            - index (@name)
            - (parameters of the model)
            - tau
            - Rt: basic or phase-dependent reproduction number
            - (dimensional parameters [day])
            - RMSLE: Root Mean Squared Log Error
            - Trials: the number of trials
            - Runtime: run time of estimation
        """
        param_dict = super().param()
        model_params = param_dict.copy()
        tau = model_params.pop(self.TAU)
        model_instance = self.model(
            population=self.population, **model_params
        )
        # Rt
        param_dict["Rt"] = model_instance.calc_r0()
        # dimensional parameters [day]
        param_dict.update(model_instance.calc_days_dict(tau))
        # RMSLE
        param_dict["RMSLE"] = self.rmsle(tau)
        # The number of trials
        param_dict["Trials"] = self.total_trials
        # Runtime
        minutes, seconds = divmod(int(self.run_time), 60)
        param_dict["Runtime"] = f"{minutes} min {seconds} sec"
        # Convert to dataframe
        df = pd.DataFrame.from_dict({name: param_dict}, orient="index")
        return df.fillna("-")

    def rmsle(self, tau):
        """
        Return RMSLE score.
        @tau <int>: tau value
        """
        score = super().rmsle(
            train_df=self.divide_minutes(tau),
            dim=1
        )
        return score

    def accuracy(self, filename=None):
        """
        Show the accuracy as a figure.
        @filename <str>: filename of the figure, or None (show figure)
        """
        tau = super().param()[self.TAU]
        train_df = self.divide_minutes(tau)
        use_variables = [
            v for (i, (p, v))
            in enumerate(zip(self.model.PRIORITIES, self.model.VARIABLES))
            if p != 0 and i != 0
        ]
        df = super().accuracy(
            train_df=train_df,
            variables=use_variables,
            filename=filename
        )
        return df
