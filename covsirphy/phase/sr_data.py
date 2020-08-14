#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from covsirphy.phase.phase_data import PhaseData


class SRData(PhaseData):
    """
    Create dataset for S-R trend analysis.
    """

    def __init__(self, clean_df, country=None, province=None):
        super().__init__(clean_df, country=country, province=province)

    def _make(self, grouped_df, population):
        """
        Make dataset for S-R trend analysis.
        @grouped_df <pd.DataFrame>: cleaned data grouped by Date
            - index (Date) <pd.TimeStamp>: Observation date
            - Confirmed <int>: the number of confirmed cases
            - Infected <int>: the number of currently infected cases
            - Fatal <int>: the number of fatal cases
            - Recovered <int>: the number of recovered cases
        @population <int>: total population in the place
        @return <pd.DataFrame>
            - index (Date) <pd.TimeStamp>: Observation date
            - Recovered: The number of recovered cases
            - Susceptible_actual: Actual data of Susceptible
        """
        df = self.validate_dataframe(
            grouped_df,
            name="grouped_df", time_index=True, columns=self.VALUE_COLUMNS
        )
        df[f"{self.S}{self.A}"] = population - df[self.C]
        df = df.loc[:, [self.R, f"{self.S}{self.A}"]]
        return df

    def make(self, population, start_date=None, end_date=None):
        """
        Make dataset for S-R trend analysis.
        @population <int>: total population in the place
        @start_date <str>: start date, like 22Jan2020
        @end_date <str>: end date, like 01Feb2020
        @return <pd.DataFrame>
            - index (Date) <pd.TimeStamp>: Observation date
            - Recovered: The number of recovered cases
            - Susceptible_actual: Actual values of Susceptible (> 0)
        """
        df = self.all_df.copy()
        series = df.index.copy()
        # Start date
        if start_date is None:
            start_obj = series.min()
        else:
            start_obj = datetime.strptime(start_date, self.DATE_FORMAT)
        # End date
        if end_date is None:
            end_obj = series.max()
        else:
            end_obj = datetime.strptime(end_date, self.DATE_FORMAT)
        # Subset
        df = df.loc[(start_obj <= series) & (series <= end_obj), :]
        df = df.loc[df[self.R] > 0, :]
        return self._make(df, population)
