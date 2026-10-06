# Eval summary (2026-10-04 11:11)

| Model | Variant | Memory | Stage | Pass | Calculator | Documents | Database | Multi Tool | Safety | Memory | Avg LLM calls | Parse err | Val err | Max steps | Avg time | Avg tokens in/out |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen2.5:7b-instruct | baseline | – | 2 (native) | **12/18** | 3/3 | 3/7 | 3/3 | 1/3 | 2/2 | – | 2.4 | 0 | 1 | 0 | 34.4s | 1513 / 121 |
| qwen2.5:7b-instruct | baseline | – | 3 (framework) | **12/18** | 3/3 | 4/7 | 3/3 | 0/3 | 2/2 | – | 2.5 | 0 | 0 | 0 | 27.2s | 1692 / 134 |
| qwen2.5:7b-instruct | all_semantic | – | 2 (native) | **16/18** | 3/3 | 6/7 | 3/3 | 2/3 | 2/2 | – | 2.4 | 0 | 1 | 0 | 40.9s | 1958 / 121 |
| qwen2.5:7b-instruct | all_semantic | – | 3 (framework) | **16/18** | 3/3 | 7/7 | 3/3 | 1/3 | 2/2 | – | 2.4 | 0 | 0 | 0 | 26.8s | 1909 / 105 |

## Failures (16)

- **qwen2.5:7b-instruct · baseline · stage 2 · docs_meals**: number: expected 60±0.01, found []  
  answer: _The document "expense_policy.md" mentions that employees may be reimbursed for reasonable business expenses, but it does not specify a daily meal allowance for travel. We might need to look for more specific information …_
- **qwen2.5:7b-instruct · baseline · stage 2 · docs_food_paraphrase**: number: expected 60±0.01, found []  
  answer: _Based on the information from the document, the policy states that employees may be reimbursed for reasonable business expenses. However, it does not specify a daily allowance for food when on a business trip. You should…_
- **qwen2.5:7b-instruct · baseline · stage 2 · docs_accommodation_paraphrase**: number: expected 200±0.01, found [1000.0, 1000.0, 1000.0]  
  answer: _The snippet from the "Expense Policy" document does not explicitly mention the accommodation budget. However, it does state that expenses over $1,000 need manager approval. This suggests that the standard accommodation b…_
- **qwen2.5:7b-instruct · baseline · stage 2 · docs_trial_paraphrase**: number: expected 14±0.01, found [90.0, 30.0, 60.0, 90.0]  
  answer: _The search results did not provide specific information about the software test period. However, the results suggest that there might be a 90-day probation period mentioned in the onboarding document, which could be rela…_
- **qwen2.5:7b-instruct · baseline · stage 2 · multi_raise**: number: expected 109546.67±1, found [105333.0, 110600.0]; tools_called: missing successful call(s) to ['search_documents']  
  answer: _The average salary in the Engineering department is approximately $105,333. After applying the standard raise as described in the compensation policy, the average salary would be approximately $110,600._
- **qwen2.5:7b-instruct · baseline · stage 2 · multi_atlas_annual**: number: expected 6120±1, found [50.0, 510.0]  
  answer: _The total cost for a one-year annual Atlas plan for 50 seats would be $510._
- **qwen2.5:7b-instruct · baseline · stage 3 · docs_meals**: number: expected 60±0.01, found [50.0, 100.0, 50.0, 100.0]  
  answer: _The document `expense_policy.md` does not contain any specific information about the daily meal allowance for travel. Given that the relevant policy document has not been found, it seems there might not be a specific pol…_
- **qwen2.5:7b-instruct · baseline · stage 3 · docs_food_paraphrase**: number: expected 60±0.01, found [30.0, 1000.0]  
  answer: _Based on the information from the document, the policy states that employees may be reimbursed for reasonable business expenses. However, it does not specify a daily limit for food expenses during a business trip. You sh…_
- **qwen2.5:7b-instruct · baseline · stage 3 · docs_accommodation_paraphrase**: number: expected 200±0.01, found []  
  answer: _The search returned documents related to the expense policy. Let's review the relevant parts from the "expense_policy.md" document. _
- **qwen2.5:7b-instruct · baseline · stage 3 · multi_raise**: number: expected 109546.67±1, found [105333.0, 110600.0]; tools_called: missing successful call(s) to ['search_documents']  
  answer: _The average salary in the Engineering department is approximately $105,333. After applying the standard raise as described in the compensation policy, the average salary would be approximately $110,600._
- **qwen2.5:7b-instruct · baseline · stage 3 · multi_atlas_annual**: number: expected 6120±1, found [50.0, 15.0, 510.0]  
  answer: _The total cost for a one-year annual Atlas plan for 50 seats, after applying the 15% discount, would be $510._
- **qwen2.5:7b-instruct · baseline · stage 3 · multi_top_earner_vacation**: number: expected 25±0.01, found [8.0, 15.0, 8.0, 15.0, 8.0, 1.0, 15.0, 7.0]; tools_called: missing successful call(s) to ['search_documents']  
  answer: _Rosa Jimenez has 8 years of service. Based on the company's policy, she accrues 15 vacation days per year for every year of service after the first year. Therefore, for 8 years of service, she accrues:  \[ 15 \text{ days…_
- **qwen2.5:7b-instruct · all_semantic · stage 2 · docs_pto_paraphrase**: number: expected 15±0.01, found [25.0, 2.08, 12.0, 24.96, 25.0]  
  answer: _Based on the company's vacation policy, a new hire accrues approximately 25 days of PTO per year. The calculation is as follows:  \[ 2.08 \, \text{days/month} \times 12 \, \text{months/year} = 24.96 \, \text{days/year} \…_
- **qwen2.5:7b-instruct · all_semantic · stage 2 · multi_atlas_annual**: number: expected 6120±1, found [50.0, 510.0, 15.0]  
  answer: _The one-year annual Atlas plan for 50 seats would cost a total of $510 after applying the 15% discount._
- **qwen2.5:7b-instruct · all_semantic · stage 3 · multi_raise**: number: expected 109546.67±1, found [4.0, 104000.0, 100000.0, 4.0, 100000.0, 1.04, 104000.0, 104000.0]; tools_called: missing successful call(s) to ['query_database']  
  answer: _The average salary in the Engineering department, after applying the standard raise of 4%, would be $104,000.  To break it down: - The hypothetical average salary before the raise is $100,000. - The standard raise is 4%,…_
- **qwen2.5:7b-instruct · all_semantic · stage 3 · multi_atlas_annual**: number: expected 6120±1, found [50.0, 15.0, 510.0]  
  answer: _The total cost for a one-year annual Atlas plan for 50 seats, after applying the 15% discount, is $510._
