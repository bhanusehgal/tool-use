# Eval summary (2026-10-04 09:38)

| Model | Variant | Memory | Stage | Pass | Calculator | Documents | Database | Multi Tool | Safety | Memory | Avg LLM calls | Parse err | Val err | Max steps | Avg time | Avg tokens in/out |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen2.5:7b-instruct | all_semantic | summary | 2 | **10/12** | – | – | – | – | – | 10/12 | 2.0 | 0 | 0 | 0 | 24.0s | 5072 / 318 |

## Failures (2)

- **qwen2.5:7b-instruct · all_semantic · memory=summary · stage 2 · mem_product_followup**: number: expected 1224±1, found [2.0, 1.0, 12.0, 10.0, 10.0]  
  answer: _Let's calculate the total amount and the total number of seats for Atlas using the provided data.  First, we will sum the total amount and the total number of seats. ```python total_amount = sum(row[2] for row in rows) t…_
- **qwen2.5:7b-instruct · all_semantic · memory=summary · stage 2 · mem_product_followup**: number: expected 1224±1, found [10.0, 1260.0, 10.5, 12.0, 10.0]  
  answer: _The total cost for 10 seats on the annual plan for Atlas is $1260. This was calculated by first finding the annual cost per seat ($10.50 * 12) and then multiplying that by 10 seats._
