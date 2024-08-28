import polars as pl
from tqdm.auto import tqdm
from typing import Dict, List, Optional
import pandas as pd

# Desired columns, in desired order
COL_ORDERS = ['hash', 'source', 'from', 'to', 'value', 'symbol', 'sub_type']#, 'transaction_fee', 'type', 'ETH_adj'] # Theses last 3 columns comes from the etc_traced file only!

# Folders and hashes identifying files in each folder
hashes_to_parse = [
    ["./Data/ABCD 24-03-17 01", "0xe96df8f5ef1a8790415068c798765b07d57643bd"],
    ["./Data/AFY", "0xf43e889444e95a0429c32b0b601dc16edf90fdbf"],
    ["./Data/BRETT 24-03-20 3j", "0xBA3F945812a83471d709BCe9C3CA699A19FB46f7"],
    ["./Data/BRETT 24-03-28 2j", "0xBA3F945812a83471d709BCe9C3CA699A19FB46f7"],
    ["./Data/ECT", "0x5b49001c8b756ab44b6ec3bcd1ea3f3a1c3cd758"],
    ["./Data/ORCH", "0x61738277ff9b92e91b8ee02c0b73e8369b79ccfc"],
    ["./Data/PEPE UniV2 24-04-05 all", "0x76fc8dbf2022ee75612cb74ec80caf6b3ccffb23"],
    ["./Data/TOSHI 24-03-24 3j", "0x4b0Aaf3EBb163dd45F663b38b6d93f6093EBC2d3"],
    ["./Data/TOSHI 24-04-28 3j", "0x4b0Aaf3EBb163dd45F663b38b6d93f6093EBC2d3"],
]

# load data
# For each pair (folder, hash), get the 5 relvant files and load them as pl.DataFrames. Then return the 5 dfs in a dictionary.
def load_data(path: str, src_hash: str) -> Dict[str, pl.DataFrame]:
    """Load Excel files and return a Dict with all of them as DataFrames"""
    data = {}
    
    filenames = {
        "main": f"{path}/TX_Main_Pool_or_Add_{src_hash}_formatted.xlsx",
        "internal": f"{path}/TX_Internes_Pool_or_Add_{src_hash}_formatted.xlsx",
        "erc_full": f"{path}/TX_ERCFull_Pool_or_Add_{src_hash}_formatted.xlsx",
        "erc_traced": f"{path}/TX_ERC_Traced_Cleaned_{src_hash}.xlsx",
        "erc": f"{path}/TX_ERC_Pool_or_Add_{src_hash}_formatted.xlsx"
    }

    for name, filename in filenames.items():
        try:
            data[name] = pl.read_excel(filename)
            print(f"{name.capitalize()} DataFrame loaded successfully. Shape: {data[name].shape}")
        except FileNotFoundError:
            print(f"File for {name} not found: {filename}")
            data[name] = pl.DataFrame()  # Empty DataFrame if file not found

    return data

# Processing each of the 5 dfs

## Main
def process_main_df(df: pl.DataFrame) -> pl.DataFrame:    
    # Process the DataFrame
    df = (
        df
        .select(['hash', 'from', 'to', 'value'])  # Select initial columns
        .with_columns([
            # pl.lit(None).cast(pl.Float64).alias("transaction_fee"),  # cast 'fee'
            pl.col("value").cast(pl.Float64),  # Cast 'value'
            pl.lit("ETH").cast(pl.Utf8).alias("symbol"),  # Add 'symbol' column
            pl.lit("main").cast(pl.Utf8).alias("source"),  # Add 'source' column
            pl.lit("main").cast(pl.Utf8).alias("sub_type"),  # Add 'sub_type' column
            # pl.lit(None).cast(pl.Utf8).alias("type"),  # Add 'type' column with None value
            # pl.lit(None).cast(pl.Float64).alias("ETH_adj"),  # Add 'ETH_adj' column with None value
        ])
    )
    
    # Ensure columns are in the specified order
    df = df.select(COL_ORDERS)
    
    print("Processed Main DataFrame shape:", df.shape)
    return df

## Internal
def process_internal_df(df: pl.DataFrame) -> pl.DataFrame:
    # Process the DataFrame
    df = (
        df
        .select(['hash', 'from', 'to', 'value', 'callType'])  # Select relevant columns
        .with_columns([
            pl.col("callType").cast(pl.Utf8).alias("sub_type"),  # Rename and cast 'callType' to 'sub_type'
            pl.col("value").cast(pl.Float64).alias("value"),  # Cast 'value' to Float64 and rename
            pl.lit("ETH").cast(pl.Utf8).alias("symbol"),  # Add 'symbol' column with constant value 'ETH'
            pl.lit("internal").cast(pl.Utf8).alias("source"),  # Add 'source' column with constant value 'internal'
            # pl.lit(None).cast(pl.Float64).alias("transaction_fee"),  # Add 'transaction_fee' column with None value
            # pl.lit(None).cast(pl.Utf8).alias("type"),  # Add 'type' column with None value
            # pl.lit(None).cast(pl.Float64).alias("ETH_adj")  # Add 'ETH_adj' column with None value
        ])
    )
    
    # Ensure columns are in the specified order
    df = df.select(COL_ORDERS)
    
    # Print the shape of the processed DataFrame
    print("Processed Internal DataFrame shape:", df.shape)
    
    # Return the processed DataFrame
    return df

## ERC full
def process_erc_full_df(df: pl.DataFrame) -> pl.DataFrame:
    """Process the ERC Full DataFrame."""
    df = (
        df
        .select(['hash', 'from', 'to', 'tokenSymbol', 'value', 'tx_type'])  # Select relevant columns
        .with_columns([
            pl.col("tokenSymbol").cast(pl.Utf8).alias("symbol"),  # Rename and cast 'tokenSymbol' to 'symbol'
            pl.col("tx_type").cast(pl.Utf8).alias("sub_type"),  # Rename and cast 'tx_type' to 'sub_type'
            pl.col("value").cast(pl.Float64).alias("value"),  # Cast 'value' to Float64
            pl.lit("erc_full").cast(pl.Utf8).alias("source"),  # Add 'source' column with constant value 'erc_full'
            # pl.lit(None).cast(pl.Float64).alias("transaction_fee"),  # Add 'transaction_fee' column with None value
            # pl.lit(None).cast(pl.Utf8).alias("type"),  # Add 'type' column with None value
            # pl.lit(None).cast(pl.Float64).alias("ETH_adj")  # Add 'ETH_adj' column with None value
        ])
    )
    
    # Ensure columns are in the specified order
    df = df.select(COL_ORDERS)
    
    # Print the shape of the processed DataFrame
    print("Processed ERC Full DataFrame shape:", df.shape)
    
    # Return the processed DataFrame
    return df

## ERC traced
def process_erc_traced_df(df: pl.DataFrame) -> pl.DataFrame:
    """Process the ERC Traced DataFrame."""
    df = (
        df
        .select(['Tx hash', 'Tx type', 'final_value', 'Fee value'])  # Select relevant columns
        .with_columns([
            pl.col("Tx hash").cast(pl.Utf8).alias("hash"),  # Rename and cast 'Tx hash' to 'hash'
            pl.col("Tx type").cast(pl.Utf8).alias("type"),  # Rename and cast 'Tx type' to 'type'
            pl.col("final_value").cast(pl.Float64).alias("ETH_adj"),  # Cast 'final_value' to 'ETH_adj'
            pl.col("Fee value").cast(pl.Float64).alias("transaction_fee"),  # Cast 'Fee value' to 'transaction_fee'
             ])
    )
    
    # Ensure columns are in the specified order
    df = df.select(["hash", "type", "ETH_adj", "transaction_fee"])
    
    # Print the shape of the processed DataFrame
    print("Processed ERC Traced DataFrame shape:", df.shape)
    
    # Return the processed DataFrame
    return df


## ERC
def process_erc_df(df: pl.DataFrame) -> pl.DataFrame:
    """Process the ERC DataFrame."""
    df = (
        df
        .select(['hash', 'from', 'to', 'tokenSymbol', 'value', 'tx_type', 'transactionFee'])  # Select relevant columns
        .with_columns([
            pl.col("tokenSymbol").cast(pl.Utf8).alias("symbol"),  # Rename and cast 'tokenSymbol' to 'symbol'
            pl.col("tx_type").cast(pl.Utf8).alias("sub_type"),  # Rename and cast 'tx_type' to 'sub_type'
            pl.col("value").cast(pl.Float64).alias("value"),  # Cast 'value' to Float64
            # pl.col("transactionFee").cast(pl.Float64).alias("transaction_fee"),  # Cast 'transactionFee' to 'transaction_fee'
            pl.lit("erc").cast(pl.Utf8).alias("source"),  # Add 'source' column with constant value 'erc'
            # pl.lit(None).cast(pl.Utf8).alias("type"),  # Add 'type' column with None value
            # pl.lit(None).cast(pl.Float64).alias("ETH_adj")  # Add 'ETH_adj' column with None value
        ])
    )
    
    # Ensure columns are in the specified order
    df = df.select(COL_ORDERS)
    
    # Print the shape of the processed DataFrame
    print("Processed ERC DataFrame shape:", df.shape)
    
    # Return the processed DataFrame
    return df

# Concatenate and join
def concatenate_and_process_dataframes(dfs: Dict[str, pl.DataFrame]) -> pl.DataFrame:
    """Concatenate and process DataFrames."""
    # Align columns before concatenation
    dfs_aligned = dfs
    
    df = (
        pl.concat([dfs_aligned['main'], dfs_aligned['internal'], dfs_aligned['erc_full'], dfs_aligned['erc']])
        .sort(["hash", "source", "from", "to"])
    )
    print("Concatenated DataFrame shape before join:", df.shape)
    
    if not dfs_aligned['erc_traced'].is_empty():
        df = df.join(dfs_aligned['erc_traced'], on="hash", how="left")
        print("DataFrame shape after join with ERC Traced:", df.shape)

    print("DataFrame shape:", df.shape)

    # Remove duplicate rows, maybe it is unnecessary
    df_unique = df.unique()
    
    print("DataFrame shape after removing duplicates:", df_unique.shape)
    return df_unique

def main() -> pl.DataFrame:
    """Process all data and return a unique final DataFrame."""    
    all_dfs = []
    for path, src_hash in tqdm(hashes_to_parse):
        data = load_data(path, src_hash)
        processed_dfs = {
            'main': process_main_df(data['main']),
            'internal': process_internal_df(data['internal']),
            'erc_full': process_erc_full_df(data['erc_full']),
            'erc_traced': process_erc_traced_df(data['erc_traced']),
            'erc': process_erc_df(data['erc'])
        }
        final_df = concatenate_and_process_dataframes(processed_dfs)
        all_dfs.append(final_df)
    
    if all_dfs:
        return pl.concat(all_dfs)
    else:
        return pl.DataFrame(columns=COL_ORDERS)

def write_parquet(df: pl.DataFrame, filename: str) -> None:
    """Write the final DataFrame to a Parquet file."""
    df.write_parquet(filename)
    print(f"Data written to {filename}")

if __name__ == "__main__":
    final_df = main()
    write_parquet(final_df, "./data/final_df.pqt")


# %%
final_df['transaction_fee'].is_null().all()

# %%
# Convert to pandas DataFrame
df_pandas = final_df.to_pandas()

# Check if the column 'type' is entirely NaN
is_empty = df_pandas['type'].isna().all()
print(is_empty)  # Output: True

# %%
# Convert to pandas DataFrame
df_pandas = final_df.to_pandas()

# Check if the column 'ETH_adj' is entirely NaN
is_empty = df_pandas['ETH_adj'].isna().all()
print(is_empty)  # Output: True


