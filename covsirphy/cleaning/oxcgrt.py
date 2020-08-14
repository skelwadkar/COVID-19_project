#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
from covsirphy.cleaning.cbase import CleaningBase


class OxCGRTData(CleaningBase):
    """
    Data cleaning of OxCGRT dataset.
    """
    COL_DICT = {
        "GovernmentResponseIndexForDisplay": "Government response index",
        "ContainmentHealthIndexForDisplay": "Containment and health index",
        "StringencyIndexForDisplay": "Stringency index",
        "EconomicSupportIndexForDisplay": "Economic support index"
    }

    def __init__(self, filename):
        super().__init__(filename)

    def cleaning(self):
        """
        Perform data cleaning of the raw data.
        This method overwrite super().cleaning() method.
        Policy indices (Overall etc.) are from
         README.md and documentation/index_methodology.md in
         https://github.com/OxCGRT/covid-policy-tracker/
        @return <pd.DataFrame>
            - index <int>: reset index
            - Date <pd.TimeStamp>: Observation date
            - Country <str>: country/region name
            - ISO3 <str>: ISO 3166-1 alpha-3, like JPN
            - other column names are defined by OxCGRT.COL_DICT
        """
        df = self._raw.copy()
        # Rename the columns
        df = df.rename(self.COL_DICT, axis=1)
        df = df.rename(
            {"CountryName": self.COUNTRY, "Date": self.DATE, "CountryCode": self.ISO3},
            axis=1
        )
        # Read date records
        df[self.DATE] = pd.to_datetime(df[self.DATE], format="%Y%m%d")
        # Confirm float type
        float_cols = list(self.COL_DICT.values())
        for col in float_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].fillna(method="ffill")
        # Select the columns to use
        df = df.loc[:, [self.DATE, self.COUNTRY, self.ISO3, *float_cols]]
        return df

    def total(self):
        """
        Cannot be used.
        """
        raise AttributeError("This method is not defined.")

    def subset(self, country=None, iso3=None):
        """
        Create a subset for a country.
        One of @country and @iso3 must be specified.
            @country <str>: country name
            @iso3 <str>: ISO 3166-1 alpha-3, like JPN
        @return <pd.DataFrame>
            - index <int>: reset index
            - Date <pd.TimeStamp>: Observation date
            - other column names are defined by OxCGRT.COL_DICT
        """
        df = self._cleaned_df.copy()
        if country is None and iso3 is None:
            raise ValueError("One of @country and @iso3 must be specified.")
        if iso3 is not None:
            if country is not None:
                raise ValueError("Either @country or @iso3 must be used.")
            iso_df = df.loc[:, [self.ISO3, self.COUNTRY]].drop_duplicates()
            iso_dict = iso_df.set_index(self.ISO3).to_dict()[self.COUNTRY]
            try:
                country = iso_dict[iso3]
            except KeyError:
                raise KeyError(f"@iso3 {iso3} is not included in this dataset.")
        df = df.loc[df[self.COUNTRY] == country, :]
        df = df.drop([self.COUNTRY, self.ISO3], axis=1).groupby(self.DATE).last()
        df = df.reset_index()
        if df.empty:
            raise KeyError(f"@country {country} is not included in the dataset.")
        return df
