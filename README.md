# Transaction Tracing on the Ethereum Platform

Contract research project in collaboration with the Autorité des marchés financiers (AMF), Québec's financial markets regulator. The goal was to develop a complementary graph-based approach to improve transaction tracing on the Ethereum blockchain.
This was a team project. I was the main author of the published report.

---

# Problem

The AMF needed a more robust method for determining the total value of complex DeFi transactions expressed in WETH, where multiple sub-transactions are involved across different addresses.

---

# Approach

Received transaction data from the AMF covering five dates in March–April 2024; performed data cleaning and restructuring to create a working dataframe grouped by transaction hash.

Modelled each transaction as a labeled multidigraph — nodes represent addresses, arcs represent token transfers.

Implemented a graph-based algorithm using Breadth-First Search (BFS) to trace transaction value in WETH/ETH, handling edge cases including flow-conservation nodes and monochromatic paths.

Evaluated results by comparing against the AMF's existing ETH estimates across 20 transaction types.

---

# Tools

Python, pandas, NumPy, graph traversal algorithms, Jupyter Notebooks, Git

---

# Results

99.99% tracing accuracy on swap transactions — the most common transaction type.

Matched or exceeded the AMF benchmark in 14 of 20 transaction categories.

Findings published in Les Cahiers du GERAD, 14th Montréal Industrial Problem Solving Workshop, 2024, pp. 33–52.
