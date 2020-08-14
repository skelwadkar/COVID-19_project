# CovsirPhy: COVID-19 data with SIR model [![GitHub license](https://img.shields.io/github/license/lisphilar/covid19-sir)](https://github.com/lisphilar/covid19-sir/blob/master/LICENSE)[![Python version](https://img.shields.io/badge/Python-3.7|3.8-green.svg)](https://www.python.org/)

## Introduction
CovsirPhy is a Python package for COVID-19 (Coronavirus disease 2019) data analysis with SIR-derived models. Please refer to "Method" part of [COVID-19 data with SIR model](https://www.kaggle.com/lisphilar/covid-19-data-with-sir-model) notebook in Kaggle to understand the methods of analysis.

With CovsirPhy, we can apply epidemic models to COVID-19 data. Epidemic models include simple SIR and SIR-F model. SIR-F is a customized SIR-derived ODE model. To evaluate the effect of measures, parameter estimation of SIR-F will be applied to subsets of time series data in each country. Parameter change points will be determined by S-R trend analysis.

## Functionalities
- Data cleaning
    - Epidemic data: raw data must include date, country, (province), the number of confirmed/fatal/recovered cases
    - Population data: raw data must include country, (province), values of population
- Data visualization with Matplotlib
- S-R Trend analysis with Optuna and scipy.optimize.curve_fit
- Numerical simulation of ODE models with scipy.integrate.solve_ivp
- Description of ODE models
    - Basic class of ODE models
    - SIR, SIR-D, SIR-F, SIR-FV and SEWIR-F model
- Parameter Estimation of ODE models with Optuna and numerical simulation
- Simulate the number of cases with user-defined parameter values

## Inspiration
- Monitor the spread of COVID-19
- Keep track parameter values/reproductive number in each country/province
- Find the relationship of reproductive number and measures taken in each country/province

## Acknowledgement
Lisphilar, 2020, Kaggle notebook, COVID-19 data with SIR model, https://www.kaggle.com/lisphilar/covid-19-data-with-sir-model

CovsirPhy development team, 2020, GitHub repository, CovsirPhy, Python package for COVID-19 data with SIR model, https://github.com/lisphilar/covid19-sir
