# Eval summary (2026-10-04 09:23)

| Model | Variant | Memory | Stage | Pass | Calculator | Documents | Database | Multi Tool | Safety | Memory | Avg LLM calls | Parse err | Val err | Max steps | Avg time | Avg tokens in/out |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen2.5:7b-instruct | all_semantic | none | 2 | **2/12** | – | – | – | – | – | 2/12 | 2.0 | 0 | 0 | 0 | 13.5s | 3532 / 303 |
| qwen2.5:7b-instruct | all_semantic | full | 2 | **10/12** | – | – | – | – | – | 10/12 | 2.0 | 0 | 0 | 0 | 11.7s | 4355 / 236 |
| qwen2.5:7b-instruct | all_semantic | window | 2 | **8/12** | – | – | – | – | – | 8/12 | 2.0 | 0 | 0 | 0 | 11.4s | 4215 / 236 |
| qwen2.5:7b-instruct | all_semantic | trim | 2 | **10/12** | – | – | – | – | – | 10/12 | 2.0 | 0 | 0 | 0 | 11.3s | 4223 / 233 |
| qwen2.5:7b-instruct | all_semantic | summary | 2 | **10/12** | – | – | – | – | – | 10/12 | 2.0 | 0 | 0 | 0 | 9.7s | 4354 / 232 |

## Failures (20)

- **qwen2.5:7b-instruct · all_semantic · memory=none · stage 2 · mem_followup_salary**: number: expected 105333.33±1, found []; tools_called: missing successful call(s) to ['query_database']  
  answer: _To answer your question, I need to know which department you're referring to. Could you please specify the department name?_
- **qwen2.5:7b-instruct · all_semantic · memory=none · stage 2 · mem_followup_salary**: number: expected 105333.33±1, found []; tools_called: missing successful call(s) to ['query_database']  
  answer: _To answer your question, I need to know which department you're referring to. Could you please specify the department name?_
- **qwen2.5:7b-instruct · all_semantic · memory=none · stage 2 · mem_pronoun_hired**: number: expected 2015±0.01, found []  
  answer: _To answer this question, I need to know the name or ID of the employee in question. Could you please provide that information?_
- **qwen2.5:7b-instruct · all_semantic · memory=none · stage 2 · mem_pronoun_hired**: number: expected 2015±0.01, found []  
  answer: _To answer this question, I need to know the name or ID of the employee in question. Could you please provide that information?_
- **qwen2.5:7b-instruct · all_semantic · memory=none · stage 2 · mem_policy_then_math**: number: expected 300±0.01, found []  
  answer: _To accurately answer your question, I need to know the daily cost or expense associated with the trip. Could you please provide me with the daily rate or any relevant details about the trip's expenses? If you're referrin…_
- **qwen2.5:7b-instruct · all_semantic · memory=none · stage 2 · mem_policy_then_math**: number: expected 300±0.01, found []  
  answer: _To accurately answer your question, I need to know the daily cost or expense associated with the trip. Could you please provide me with the daily rate or any relevant details about the trip's expenses? If you're referrin…_
- **qwen2.5:7b-instruct · all_semantic · memory=none · stage 2 · mem_correction**: tools_called: missing successful call(s) to ['query_database']  
  answer: _Based on the search results, here are some key policies for the Marketing department:  1. **Expense Policy**: Employees may be reimbursed for reasonable business expenses. 2. **Compensation Policy**: For the current revi…_
- **qwen2.5:7b-instruct · all_semantic · memory=none · stage 2 · mem_correction**: tools_called: missing successful call(s) to ['query_database']  
  answer: _Based on the search results, here are some key policies for the Marketing department:  1. **Expense Policy**: Employees may be reimbursed for reasonable business expenses. 2. **Compensation Policy**: For the current revi…_
- **qwen2.5:7b-instruct · all_semantic · memory=full · stage 2 · mem_product_followup**: number: expected 1224±1, found [10.0, 1440.0, 10.0, 12.0, 10.0, 120.0, 12.0, 120.0]  
  answer: _The total cost for 10 seats on the annual plan for Atlas is $1,440.   This was calculated by first finding the monthly cost for 10 seats ($12 * 10 = $120), and then multiplying that by 12 months to get the annual cost ($…_
- **qwen2.5:7b-instruct · all_semantic · memory=full · stage 2 · mem_product_followup**: number: expected 1224±1, found [10.0, 1260.0, 10.5, 12.0, 10.0]  
  answer: _The total cost for 10 seats on the annual plan for Atlas is $1260. This was calculated by first finding the annual cost per seat ($10.50 * 12) and then multiplying that by 10 seats._
- **qwen2.5:7b-instruct · all_semantic · memory=window · stage 2 · mem_product_followup**: number: expected 1224±1, found [10.0, 1260.0, 10.5, 12.0, 10.0]  
  answer: _The total cost for 10 seats on the annual plan for Atlas is $1260. This was calculated by first finding the annual cost per seat ($10.50 * 12) and then multiplying that by 10 seats._
- **qwen2.5:7b-instruct · all_semantic · memory=window · stage 2 · mem_product_followup**: number: expected 1224±1, found [10.0, 1260.0, 10.5, 12.0, 10.0]  
  answer: _The total cost for 10 seats on the annual plan for Atlas is $1260. This was calculated by first finding the annual cost per seat ($10.50 * 12) and then multiplying that by 10 seats._
- **qwen2.5:7b-instruct · all_semantic · memory=trim · stage 2 · mem_product_followup**: number: expected 1224±1, found [10.0, 1260.0, 10.5, 12.0, 10.0]  
  answer: _The total cost for 10 seats on the annual plan for Atlas is $1260. This was calculated by first finding the annual cost per seat ($10.50 * 12) and then multiplying that by 10 seats._
- **qwen2.5:7b-instruct · all_semantic · memory=trim · stage 2 · mem_product_followup**: number: expected 1224±1, found [10.0, 1260.0, 10.5, 12.0, 10.0]  
  answer: _The total cost for 10 seats on the annual plan for Atlas is $1260. This was calculated by first finding the annual cost per seat ($10.50 * 12) and then multiplying that by 10 seats._
- **qwen2.5:7b-instruct · all_semantic · memory=summary · stage 2 · mem_product_followup**: number: expected 1224±1, found [10.0, 1260.0, 10.5, 12.0, 10.0]  
  answer: _The total cost for 10 seats on the annual plan for Atlas is $1260. This was calculated by first finding the annual cost per seat ($10.50 * 12) and then multiplying that by 10 seats._
- **qwen2.5:7b-instruct · all_semantic · memory=summary · stage 2 · mem_product_followup**: number: expected 1224±1, found [10.0, 1440.0, 12.0, 10.0, 12.0]  
  answer: _The total cost for 10 seats for one year on the Atlas annual plan is $1,440.  This was calculated by multiplying the monthly cost per seat ($12) by 10 seats, and then by 12 months to get the annual cost._
- **qwen2.5:7b-instruct · all_semantic · memory=none · stage 2 · mem_fact_from_turn1**: number: expected 4±0.01, found []  
  answer: _It appears there are no employees listed in your department according to the database. This could be due to a few reasons such as recent changes not yet reflected in the database, or an error in the data. Please verify t…_
- **qwen2.5:7b-instruct · all_semantic · memory=none · stage 2 · mem_fact_from_turn1**: number: expected 4±0.01, found []  
  answer: _It appears there are no employees listed in your department according to the database. This could be due to a few reasons, such as the department not being correctly identified or the data not being up-to-date.   Would y…_
- **qwen2.5:7b-instruct · all_semantic · memory=window · stage 2 · mem_fact_from_turn1**: number: expected 4±0.01, found [0.0]  
  answer: _It appears that there are currently 0 employees in your team according to the database._
- **qwen2.5:7b-instruct · all_semantic · memory=window · stage 2 · mem_fact_from_turn1**: number: expected 4±0.01, found [0.0]  
  answer: _It appears that there are currently 0 employees in your team according to the database._
