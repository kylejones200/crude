from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType
)

assays_schema = StructType([
    StructField("crude_id", StringType(), False),
    StructField("name", StringType(), True),
    StructField("api", DoubleType(), True),
    StructField("sulfur_wt", DoubleType(), True),
    StructField("cut_light_pct", DoubleType(), True),
    StructField("cut_middle_pct", DoubleType(), True),
    StructField("cut_heavy_pct", DoubleType(), True),
])

prices_schema = StructType([
    StructField("product", StringType(), False),
    StructField("price_usd_bbl", DoubleType(), True),
])

freight_schema = StructType([
    StructField("origin", StringType(), False),
    StructField("destination", StringType(), False),
    StructField("rate_usd_bbl", DoubleType(), True),
])
