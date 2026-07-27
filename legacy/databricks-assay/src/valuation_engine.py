from pyspark.sql import DataFrame
from pyspark.sql import functions as F

# Simple mapping from assay cuts to product baskets
CUT_TO_PRODUCT = {
    "cut_light_pct": "LIGHTS",
    "cut_middle_pct": "MIDDLES",
    "cut_heavy_pct": "HEAVIES",
}


def compute_crude_value(assays: DataFrame, prices: DataFrame) -> DataFrame:
    """
    Returns a DataFrame with columns: crude_id, gross_value_usd_bbl
    gross_value_usd_bbl = sum_i (cut_pct_i * price(product_i))
    """
    # Pivot prices to columns for easy reference
    price_cols = [F.first("price_usd_bbl").alias(p) for p in CUT_TO_PRODUCT.values()]
    prices_pivot = (
        prices.groupBy().pivot("product", list(CUT_TO_PRODUCT.values())).agg(F.first("price_usd_bbl"))
    )

    joined = assays.crossJoin(prices_pivot)

    expr = None
    for cut_col, product in CUT_TO_PRODUCT.items():
        term = F.col(cut_col) * F.col(product)
        expr = term if expr is None else expr + term

    return joined.select(
        "crude_id",
        expr.alias("gross_value_usd_bbl")
    )


def apply_freight(value_df: DataFrame, freight: DataFrame, default_rate: float = 0.0, destination: str = "GulfCoast") -> DataFrame:
    """
    Subtracts freight by mapping crude_id prefix to an origin region where available.
    For demo, we map crude_id -> origin via simple rules.
    """
    # Toy mapping rules
    origin_expr = (
        F.when(F.col("crude_id") == "ARB", F.lit("ME"))
         .when(F.col("crude_id") == "WAF", F.lit("WAF"))
         .otherwise(F.lit("USG"))
         .alias("origin")
    )

    freight_rate = (
        freight.filter(F.col("destination") == F.lit(destination))
               .select("origin", "rate_usd_bbl")
    )

    with_origin = value_df.select("crude_id", "gross_value_usd_bbl", origin_expr)

    joined = with_origin.join(freight_rate, on="origin", how="left")

    result = joined.select(
        "crude_id",
        (F.col("gross_value_usd_bbl") - F.coalesce(F.col("rate_usd_bbl"), F.lit(default_rate))).alias("netback_usd_bbl")
    )

    return result
