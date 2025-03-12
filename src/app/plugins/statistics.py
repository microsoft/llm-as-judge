import numpy as np
import pandas as pd
from scipy import stats


class StatisticalAnalysisPlugin:
    """
    A plugin for performing comprehensive statistical analysis.
    
    This plugin provides:
      - Descriptive statistics: mode, median, mean, standard deviation,
        variance, coefficient of variation, kurtosis, skewness,
        and specified percentiles (quantiles).
      - Hypothesis tests:
          • Kolmogorov-Smirnov test
          • One-sample t-test and independent two-sample t-test
          • F-test for comparing variances
          • Chi-square goodness-of-fit test
      - A function to compute a matrix of these statistics for each category in a dataset.
    """

    def calculate_statistics(self, data, percentiles=[1, 5, 25, 50, 75, 95, 99]):
        """
        Calculate a comprehensive set of statistics for a 1D numeric dataset.
        
        Parameters:
            data (array-like): 1D numeric data.
            percentiles (list): List of percentiles to compute.
            
        Returns:
            dict: A dictionary containing:
                  - mode, median, mean, std, variance, coefficient_of_variation,
                  - kurtosis, skewness, and the specified percentiles.
        """
        data = np.asarray(data)
        stats_dict = {}

        mode_result = stats.mode(data, nan_policy='omit')
        mode_val = mode_result.mode[0] if mode_result.count[0] > 0 else np.nan
        stats_dict['mode'] = mode_val

        stats_dict['median'] = np.median(data)
        stats_dict['mean'] = np.mean(data)
        stats_dict['std'] = np.std(data, ddof=1)
        stats_dict['variance'] = np.var(data, ddof=1)
        stats_dict['coefficient_of_variation'] = (stats_dict['std'] / stats_dict['mean']
                                                  if stats_dict['mean'] != 0 else np.nan)
        
        stats_dict['kurtosis'] = stats.kurtosis(data, fisher=True, bias=False, nan_policy='omit')
        stats_dict['skewness'] = stats.skew(data, bias=False, nan_policy='omit')

        pct_values = np.percentile(data, percentiles)
        for perc, value in zip(percentiles, pct_values):
            stats_dict[f'percentile_{perc}'] = value
        
        return stats_dict

    def kolmogorov_smirnov_test(self, data, cdf='norm'):
        """
        Perform the Kolmogorov-Smirnov test for goodness-of-fit.

        Parameters:
            data (array-like): 1D numeric data.
            cdf (str or callable): The cumulative distribution function to compare against.
                                     Default is the normal distribution ('norm').

        Returns:
            tuple: (statistic, p_value)
        """
        data = np.asarray(data)
        result = stats.kstest(data, cdf)
        return result.statistic, result.pvalue

    def t_test_independent(self, sample1, sample2, equal_var=True):
        """
        Perform an independent two-sample t-test.

        Parameters:
            sample1, sample2 (array-like): The two samples to compare.
            equal_var (bool): Assume equal variances if True.

        Returns:
            tuple: (t_statistic, p_value)
        """
        sample1 = np.asarray(sample1)
        sample2 = np.asarray(sample2)
        result = stats.ttest_ind(sample1, sample2, equal_var=equal_var, nan_policy='omit')
        return result.statistic, result.pvalue

    def t_test_1sample(self, sample, popmean):
        """
        Perform a one-sample t-test.

        Parameters:
            sample (array-like): The sample data.
            popmean (float): The population mean to compare against.

        Returns:
            tuple: (t_statistic, p_value)
        """
        sample = np.asarray(sample)
        result = stats.ttest_1samp(sample, popmean, nan_policy='omit')
        return result.statistic, result.pvalue

    def f_test(self, sample1, sample2):
        """
        Perform an F-test for equality of variances between two samples.

        This function computes the ratio of variances and estimates a two-tailed p-value.

        Parameters:
            sample1, sample2 (array-like): The two samples to compare.

        Returns:
            tuple: (f_statistic, p_value)
        """
        sample1 = np.asarray(sample1)
        sample2 = np.asarray(sample2)
        n1, n2 = len(sample1), len(sample2)
        var1 = np.var(sample1, ddof=1)
        var2 = np.var(sample2, ddof=1)
        
        # Force the ratio to be >= 1 for a two-tailed test.
        if var1 >= var2:
            f_stat = var1 / var2
            df1, df2 = n1 - 1, n2 - 1
        else:
            f_stat = var2 / var1
            df1, df2 = n2 - 1, n1 - 1
        
        # Two-tailed p-value.
        p_value = 2 * min(stats.f.cdf(f_stat, df1, df2), 1 - stats.f.cdf(f_stat, df1, df2))
        return f_stat, p_value

    def chi_square_test(self, observed, expected):
        """
        Perform a chi-square goodness-of-fit test.

        Parameters:
            observed (array-like): Observed frequency counts.
            expected (array-like): Expected frequency counts.

        Returns:
            tuple: (chi2_statistic, p_value)
        """
        observed = np.asarray(observed)
        expected = np.asarray(expected)
        result = stats.chisquare(observed, f_exp=expected)
        return result.statistic, result.pvalue

    def compute_category_statistics(self, df, category_column, value_columns=None, percentiles=[5, 25, 50, 75, 95]):
        """
        Compute a matrix of descriptive statistics for each category in a dataset.

        For each unique value in `category_column` and for each column in `value_columns`
        (or all numeric columns except the category column if None), the following statistics are computed:
          - mode, median, mean, standard deviation, variance, coefficient of variation,
          - kurtosis, skewness, and the specified percentiles.

        The result is returned as a multi-index DataFrame where rows represent categories and
        columns are a MultiIndex (value column, statistic).

        Parameters:
            df (pandas.DataFrame): The dataset.
            category_column (str): Column name used to group the data.
            value_columns (list): List of numeric column names to analyze. If None, all numeric columns
                                  except the category column are used.
            percentiles (list): List of percentiles to compute.

        Returns:
            pandas.DataFrame: A matrix of computed statistics with a MultiIndex for columns.
        """
        if value_columns is None:
            value_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            if category_column in value_columns:
                value_columns.remove(category_column)
        
        def series_stats(series):
            return self.calculate_statistics(series.dropna(), percentiles=percentiles)
        
        grouped = df.groupby(category_column)
        
        result_dict = {}
        for cat, group in grouped:
            col_stats = {}
            for col in value_columns:
                col_stats[col] = series_stats(group[col])
            result_dict[cat] = col_stats

        final_data = {}
        for cat, stats_per_col in result_dict.items():
            df_stats = pd.DataFrame(stats_per_col).T
            final_data[cat] = df_stats.T.stack()
        
        combined_df = pd.DataFrame(final_data).T
        combined_df.columns = pd.MultiIndex.from_tuples(combined_df.columns)
        return combined_df
