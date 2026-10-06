# Eval summary (2026-10-04 03:18)

| Model | Variant | Stage | Pass | Calculator | Documents | Database | Multi Tool | Safety | Avg LLM calls | Parse err | Val err | Max steps | Avg time | Avg tokens in/out |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen2.5:7b-instruct | baseline | 1 | **2/10** | – | 2/7 | – | 0/3 | – | 3.4 | 20 | 0 | 1 | 40.5s | 2698 / 212 |
| qwen2.5:7b-instruct | baseline | 2 | **4/10** | – | 3/7 | – | 1/3 | – | 2.6 | 0 | 0 | 0 | 26.0s | 1738 / 142 |
| qwen2.5:7b-instruct | all | 1 | **6/10** | – | 5/7 | – | 1/3 | – | 3.8 | 5 | 0 | 0 | 37.1s | 3575 / 140 |
| qwen2.5:7b-instruct | all | 2 | **8/10** | – | 6/7 | – | 2/3 | – | 2.8 | 0 | 0 | 0 | 28.2s | 2278 / 126 |
| qwen2.5:7b-instruct | semantic | 1 | **4/10** | – | 2/7 | – | 2/3 | – | 3.2 | 16 | 0 | 0 | 32.9s | 2373 / 164 |
| qwen2.5:7b-instruct | semantic | 2 | **9/10** | – | 7/7 | – | 2/3 | – | 2.3 | 0 | 0 | 0 | 24.7s | 1542 / 113 |
| qwen2.5:7b-instruct | hybrid | 1 | **3/10** | – | 2/7 | – | 1/3 | – | 3.1 | 15 | 0 | 0 | 35.3s | 2414 / 177 |
| qwen2.5:7b-instruct | hybrid | 2 | **7/10** | – | 7/7 | – | 0/3 | – | 2.3 | 0 | 0 | 0 | 23.5s | 1543 / 112 |
| qwen2.5:7b-instruct | all_semantic | 1 | **9/10** | – | 7/7 | – | 2/3 | – | 2.8 | 3 | 0 | 0 | 28.4s | 2350 / 105 |
| qwen2.5:7b-instruct | all_semantic | 2 | **8/10** | – | 6/7 | – | 2/3 | – | 2.6 | 0 | 0 | 0 | 30.0s | 2113 / 128 |

## Failures (40)

- **qwen2.5:7b-instruct · baseline · stage 1 · docs_meals**: number: expected 60±0.01, found []; tools_called: missing successful call(s) to ['search_documents']  
  answer: _I was unable to find the exact policy regarding the daily meal allowance for work travel in our internal documents. I recommend checking the company's expense policy document or consulting with the HR department for the …_
- **qwen2.5:7b-instruct · baseline · stage 1 · docs_internet**: number: expected 40±0.01, found []; tools_called: missing successful call(s) to ['search_documents']  
  answer: _I couldn't find specific information about the monthly internet stipend for remote workers in our internal documents. Could you provide more details or check with the HR department?_
- **qwen2.5:7b-instruct · baseline · stage 1 · docs_food_paraphrase**: number: expected 60±0.01, found []; tools_called: missing successful call(s) to ['search_documents']  
  answer: _I encountered an issue while trying to access the company's internal documents. Typically, the amount you can spend on food each day during a business trip is detailed in the company's expense reimbursement policy. I rec…_
- **qwen2.5:7b-instruct · baseline · stage 1 · docs_accommodation_paraphrase**: number: expected 200±0.01, found []; tools_called: missing successful call(s) to ['search_documents']  
  answer: _I encountered an issue while searching the documents. Could you please provide more details or check the policy document for the specific amount allowed per night for accommodation in a normal city when traveling for wor…_
- **qwen2.5:7b-instruct · baseline · stage 1 · docs_trial_paraphrase**: number: expected 14±0.01, found []; tools_called: missing successful call(s) to ['search_documents']  
  answer: _I encountered an issue while searching the documents. Please provide more details or check the policy documents for the software testing period._
- **qwen2.5:7b-instruct · baseline · stage 1 · multi_raise**: number: expected 109546.67±1, found []; tools_called: missing successful call(s) to ['query_database']  
  answer: _To accurately calculate the average salary in the Engineering department and the adjusted salary after the standard raise, I need the current average salary for that department. Could you please provide the current avera…_
- **qwen2.5:7b-instruct · baseline · stage 1 · multi_atlas_annual**: number: expected 6120±1, found [50.0, 7200.0]  
  answer: _The total cost for a one-year annual Atlas plan for 50 seats would be $7200._
- **qwen2.5:7b-instruct · baseline · stage 1 · multi_top_earner_vacation**: finished: stop=max_steps; contains_any: expected one of ['Rosa Jimenez', 'Rosa']; number: expected 25±0.01, found [8.0]; tools_called: missing successful call(s) to ['query_database', 'search_documents']  
  answer: _[Stopped: no final answer after 8 steps]_
- **qwen2.5:7b-instruct · baseline · stage 2 · docs_meals**: number: expected 60±0.01, found []  
  answer: _The document "expense_policy.md" mentions that employees may be reimbursed for reasonable business expenses, but it does not specify a daily meal allowance for travel. We might need to look for more specific information …_
- **qwen2.5:7b-instruct · baseline · stage 2 · docs_food_paraphrase**: number: expected 60±0.01, found []  
  answer: _Based on the information from the document, the policy states that employees may be reimbursed for reasonable business expenses. However, it does not specify a daily allowance for food when on a business trip. You should…_
- **qwen2.5:7b-instruct · baseline · stage 2 · docs_accommodation_paraphrase**: number: expected 200±0.01, found []  
  answer: _It seems there isn't a specific document that addresses the accommodation budget for normal cities. Could you please provide more context or specify the location or type of city you're referring to? This will help me fin…_
- **qwen2.5:7b-instruct · baseline · stage 2 · docs_trial_paraphrase**: number: expected 14±0.01, found [90.0, 30.0, 60.0, 90.0]  
  answer: _The search results did not provide specific information about the software test period. However, the results suggest that there might be a 90-day probation period mentioned in the onboarding document, which could be rela…_
- **qwen2.5:7b-instruct · baseline · stage 2 · multi_raise**: number: expected 109546.67±1, found [105333.0, 110600.0]; tools_called: missing successful call(s) to ['search_documents']  
  answer: _The average salary in the Engineering department is approximately $105,333. After applying the standard raise as described in the compensation policy, the average salary would be approximately $110,600._
- **qwen2.5:7b-instruct · baseline · stage 2 · multi_atlas_annual**: number: expected 6120±1, found [50.0, 510.0]  
  answer: _The total cost for a one-year annual Atlas plan for 50 seats would be $510._
- **qwen2.5:7b-instruct · semantic · stage 1 · docs_meals**: number: expected 60±0.01, found []; tools_called: missing successful call(s) to ['search_documents']  
  answer: _I was unable to find the exact policy regarding daily meal allowances for work travel in our internal documents. I recommend checking with our HR department for the most accurate information._
- **qwen2.5:7b-instruct · semantic · stage 1 · docs_internet**: number: expected 40±0.01, found []; tools_called: missing successful call(s) to ['search_documents']  
  answer: _I couldn't find specific information about the monthly internet stipend for remote workers in our documents or the database. Could you provide more context or check with the HR department for the exact amount?_
- **qwen2.5:7b-instruct · semantic · stage 1 · docs_food_paraphrase**: number: expected 60±0.01, found []; tools_called: missing successful call(s) to ['search_documents']  
  answer: _I encountered an issue while searching for the company's policy on meal allowances for business trips. Could you please provide more details or check the relevant internal document?_
- **qwen2.5:7b-instruct · semantic · stage 1 · docs_accommodation_paraphrase**: number: expected 200±0.01, found []; tools_called: missing successful call(s) to ['search_documents']  
  answer: _I encountered an issue while searching the documents. Could you please provide more details or check the policy document for the specific amount?_
- **qwen2.5:7b-instruct · semantic · stage 1 · docs_trial_paraphrase**: number: expected 14±0.01, found []; tools_called: missing successful call(s) to ['search_documents']  
  answer: _I am unable to retrieve the information about the software test period for customers due to technical issues. Could you please provide the details or a range of days typically allowed for testing?_
- **qwen2.5:7b-instruct · semantic · stage 1 · multi_top_earner_vacation**: contains_any: expected one of ['Rosa Jimenez', 'Rosa']; number: expected 25±0.01, found []; tools_called: missing successful call(s) to ['query_database', 'search_documents']  
  answer: _There was an issue processing the request. Please try again later or contact support if the problem persists._
- **qwen2.5:7b-instruct · semantic · stage 2 · multi_raise**: number: expected 109546.67±1, found [105333.0, 110600.0]; tools_called: missing successful call(s) to ['search_documents']  
  answer: _The average salary in the Engineering department is approximately $105,333. After applying the standard raise as described in the compensation policy, the average salary would be approximately $110,600._
- **qwen2.5:7b-instruct · hybrid · stage 1 · docs_meals**: number: expected 60±0.01, found []; tools_called: missing successful call(s) to ['search_documents']  
  answer: _I was unable to find the exact policy regarding daily meal allowances for work travel in our internal documents. I recommend checking the company's expense reimbursement policy or contacting the HR department for the mos…_
- **qwen2.5:7b-instruct · hybrid · stage 1 · docs_internet**: number: expected 40±0.01, found []; tools_called: missing successful call(s) to ['search_documents']  
  answer: _I was unable to retrieve the specific information about the monthly internet stipend for remote workers from the company's documents. Let me check with the HR department for this detail._
- **qwen2.5:7b-instruct · hybrid · stage 1 · docs_food_paraphrase**: number: expected 60±0.01, found []; tools_called: missing successful call(s) to ['search_documents']  
  answer: _I encountered an issue while searching for the company's policy on meal allowances for business trips. Could you please provide more details or check the relevant internal document?_
- **qwen2.5:7b-instruct · hybrid · stage 1 · docs_accommodation_paraphrase**: tools_called: missing successful call(s) to ['search_documents']  
  answer: _I was unable to retrieve the specific policy from our internal documents. Typically, travel and expense reimbursement guidelines include a per diem rate for accommodation based on the city or region. For a more accurate …_
- **qwen2.5:7b-instruct · hybrid · stage 1 · docs_trial_paraphrase**: number: expected 14±0.01, found []; tools_called: missing successful call(s) to ['search_documents']  
  answer: _I encountered an issue while searching the documents. Please provide more details or check the policy documents for the specific testing period for customers._
- **qwen2.5:7b-instruct · hybrid · stage 1 · multi_atlas_annual**: number: expected 6120±1, found [50.0, 5184.0]  
  answer: _The total cost for a one-year Atlas plan for 50 seats would be $5184._
- **qwen2.5:7b-instruct · hybrid · stage 1 · multi_top_earner_vacation**: contains_any: expected one of ['Rosa Jimenez', 'Rosa']; number: expected 25±0.01, found []; tools_called: missing successful call(s) to ['query_database', 'search_documents']  
  answer: _There was an issue processing the request. Please try again later or contact support if the problem persists._
- **qwen2.5:7b-instruct · hybrid · stage 2 · multi_raise**: number: expected 109546.67±1, found [105333.0, 110600.0]; tools_called: missing successful call(s) to ['search_documents']  
  answer: _The average salary in the Engineering department is approximately $105,333. After applying the standard raise as described in the compensation policy, the average salary would be approximately $110,600._
- **qwen2.5:7b-instruct · hybrid · stage 2 · multi_atlas_annual**: number: expected 6120±1, found [50.0, 15.0, 510.0]  
  answer: _The total cost for a one-year annual Atlas plan for 50 seats, after applying the 15% discount, would be $510._
- **qwen2.5:7b-instruct · hybrid · stage 2 · multi_top_earner_vacation**: number: expected 25±0.01, found [8.0, 15.0, 10.0, 8.0, 10.0, 10.0]; tools_called: missing successful call(s) to ['search_documents']  
  answer: _Rosa Jimenez has been with the company for 8 years. Based on the company's policy, she accrues 15 vacation days per year after 10 years of service. Since she has been with the company for 8 years, she is entitled to 10 v…_
- **qwen2.5:7b-instruct · all · stage 1 · docs_food_paraphrase**: number: expected 60±0.01, found []  
  answer: _The company's policy does not specify a daily food allowance for business trips. You can be reimbursed for reasonable business expenses, but the exact amount is not defined. Please refer to the expense policy document fo…_
- **qwen2.5:7b-instruct · all · stage 1 · docs_accommodation_paraphrase**: number: expected 200±0.01, found [1000.0]  
  answer: _The policy does not specify a fixed amount for accommodation expenses per night in a normal city. It only states that employees may be reimbursed for reasonable business expenses. You should ensure that your expenses are…_
- **qwen2.5:7b-instruct · all · stage 1 · multi_raise**: number: expected 109546.67±1, found [105333.33, 4.0, 2.0, 9311.47]  
  answer: _The average salary in the Engineering department is $105,333.33 per year. After the standard raise of 4% and the additional 2% as described in the compensation policy, the average monthly salary would be approximately $9…_
- **qwen2.5:7b-instruct · all · stage 1 · multi_top_earner_vacation**: number: expected 25±0.01, found [142000.0, 18.75]  
  answer: _The highest-paid employee is Rosa Jimenez, who earns $142,000 per year. Based on her years of service, she accrues 18.75 vacation days per year._
- **qwen2.5:7b-instruct · all · stage 2 · docs_food_paraphrase**: number: expected 60±0.01, found [50.0, 100.0]  
  answer: _Based on the information provided in the expense policy document, there is no specific mention of a daily food allowance for business trips. The policy only outlines that employees may be reimbursed for reasonable busine…_
- **qwen2.5:7b-instruct · all · stage 2 · multi_raise**: number: expected 109546.67±1, found [105333.33, 4.0, 2.0, 111737.6]  
  answer: _The average salary in the Engineering department is $105,333.33. After applying the standard raise of 4% and the additional 2% as described in the compensation policy, the adjusted average salary would be approximately $…_
- **qwen2.5:7b-instruct · all_semantic · stage 1 · multi_top_earner_vacation**: number: expected 25±0.01, found [142000.0, 20.0]  
  answer: _The highest-paid employee is Rosa Jimenez with an annual salary of $142,000. Based on their years of service, Rosa Jimenez accrues 20 vacation days per year._
- **qwen2.5:7b-instruct · all_semantic · stage 2 · docs_pto_paraphrase**: number: expected 15±0.01, found [12.0, 1.0, 12.0]  
  answer: _From the documents searched, it appears that all full-time employees, including new hires, accrue paid time off (PTO) every month they are employed. However, the exact amount of PTO per year for new hires is not specifie…_
- **qwen2.5:7b-instruct · all_semantic · stage 2 · multi_atlas_annual**: number: expected 6120±1, found [50.0, 510.0, 15.0]  
  answer: _The one-year annual Atlas plan for 50 seats would cost a total of $510 after applying the 15% discount._
