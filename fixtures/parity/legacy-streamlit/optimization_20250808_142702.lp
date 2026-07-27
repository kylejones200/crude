\* CrudeInventoryOptimization *\
Minimize
Total_Cost: 68.9000015259 buy_canada_heavy_0
 + 67.3199996948 buy_canada_heavy_1 + 67.6900024414 buy_canada_heavy_2
 + 67.0100021362 buy_canada_heavy_3 + 65.4899978638 buy_canada_heavy_4
 + 63.8799972534 buy_canada_heavy_5 + 68.9000015259 buy_canada_light_0
 + 67.3199996948 buy_canada_light_1 + 67.6900024414 buy_canada_light_2
 + 67.0100021362 buy_canada_light_3 + 65.4899978638 buy_canada_light_4
 + 63.8799972534 buy_canada_light_5 + 68.9000015259 buy_canada_medium_0
 + 67.3199996948 buy_canada_medium_1 + 67.6900024414 buy_canada_medium_2
 + 67.0100021362 buy_canada_medium_3 + 65.4899978638 buy_canada_medium_4
 + 63.8799972534 buy_canada_medium_5 + 84.4000015259 buy_domestic_heavy_0
 + 82.8199996948 buy_domestic_heavy_1 + 83.1900024414 buy_domestic_heavy_2
 + 82.5100021362 buy_domestic_heavy_3 + 80.9899978638 buy_domestic_heavy_4
 + 79.3799972534 buy_domestic_heavy_5 + 84.4000015259 buy_domestic_light_0
 + 82.8199996948 buy_domestic_light_1 + 83.1900024414 buy_domestic_light_2
 + 82.5100021362 buy_domestic_light_3 + 80.9899978638 buy_domestic_light_4
 + 79.3799972534 buy_domestic_light_5 + 84.4000015259 buy_domestic_medium_0
 + 82.8199996948 buy_domestic_medium_1 + 83.1900024414 buy_domestic_medium_2
 + 82.5100021362 buy_domestic_medium_3 + 80.9899978638 buy_domestic_medium_4
 + 79.3799972534 buy_domestic_medium_5 + 87.5500030518 buy_foreign_heavy_0
 + 86.4000015259 buy_foreign_heavy_1 + 86.8099975586 buy_foreign_heavy_2
 + 86.2099990845 buy_foreign_heavy_3 + 84.8899993896 buy_foreign_heavy_4
 + 83.4499969482 buy_foreign_heavy_5 + 87.5500030518 buy_foreign_light_0
 + 86.4000015259 buy_foreign_light_1 + 86.8099975586 buy_foreign_light_2
 + 86.2099990845 buy_foreign_light_3 + 84.8899993896 buy_foreign_light_4
 + 83.4499969482 buy_foreign_light_5 + 87.5500030518 buy_foreign_medium_0
 + 86.4000015259 buy_foreign_medium_1 + 86.8099975586 buy_foreign_medium_2
 + 86.2099990845 buy_foreign_medium_3 + 84.8899993896 buy_foreign_medium_4
 + 83.4499969482 buy_foreign_medium_5 + 1000 unmet_heavy_0
 + 1000 unmet_heavy_1 + 1000 unmet_heavy_2 + 1000 unmet_heavy_3
 + 1000 unmet_heavy_4 + 1000 unmet_heavy_5 + 1000 unmet_light_0
 + 1000 unmet_light_1 + 1000 unmet_light_2 + 1000 unmet_light_3
 + 1000 unmet_light_4 + 1000 unmet_light_5 + 1000 unmet_medium_0
 + 1000 unmet_medium_1 + 1000 unmet_medium_2 + 1000 unmet_medium_3
 + 1000 unmet_medium_4 + 1000 unmet_medium_5
Subject To
Initial_Inventory_heavy: inv_heavy_0 = 20000
Initial_Inventory_light: inv_light_0 = 20000
Initial_Inventory_medium: inv_medium_0 = 20000
Inventory_Balance_heavy_1: - demand_heavy_0 + inv_heavy_0 - inv_heavy_1
 + unmet_heavy_0 = 0
Inventory_Balance_heavy_2: buy_canada_heavy_0 - demand_heavy_1 + inv_heavy_1
 - inv_heavy_2 + unmet_heavy_1 = 0
Inventory_Balance_heavy_3: buy_canada_heavy_1 + buy_foreign_heavy_0
 - demand_heavy_2 + inv_heavy_2 - inv_heavy_3 + unmet_heavy_2 = 0
Inventory_Balance_heavy_4: buy_canada_heavy_2 + buy_foreign_heavy_1
 - demand_heavy_3 + inv_heavy_3 - inv_heavy_4 + unmet_heavy_3 = 0
Inventory_Balance_heavy_5: buy_canada_heavy_3 + buy_foreign_heavy_2
 - demand_heavy_4 + inv_heavy_4 - inv_heavy_5 + unmet_heavy_4 = 0
Inventory_Balance_heavy_6: buy_canada_heavy_4 + buy_foreign_heavy_3
 - demand_heavy_5 + inv_heavy_5 - inv_heavy_6 + unmet_heavy_5 = 0
Inventory_Balance_light_1: - demand_light_0 + inv_light_0 - inv_light_1
 + unmet_light_0 = 0
Inventory_Balance_light_2: buy_canada_light_0 - demand_light_1 + inv_light_1
 - inv_light_2 + unmet_light_1 = 0
Inventory_Balance_light_3: buy_canada_light_1 + buy_foreign_light_0
 - demand_light_2 + inv_light_2 - inv_light_3 + unmet_light_2 = 0
Inventory_Balance_light_4: buy_canada_light_2 + buy_foreign_light_1
 - demand_light_3 + inv_light_3 - inv_light_4 + unmet_light_3 = 0
Inventory_Balance_light_5: buy_canada_light_3 + buy_foreign_light_2
 - demand_light_4 + inv_light_4 - inv_light_5 + unmet_light_4 = 0
Inventory_Balance_light_6: buy_canada_light_4 + buy_foreign_light_3
 - demand_light_5 + inv_light_5 - inv_light_6 + unmet_light_5 = 0
Inventory_Balance_medium_1: - demand_medium_0 + inv_medium_0 - inv_medium_1
 + unmet_medium_0 = 0
Inventory_Balance_medium_2: buy_canada_medium_0 - demand_medium_1
 + inv_medium_1 - inv_medium_2 + unmet_medium_1 = 0
Inventory_Balance_medium_3: buy_canada_medium_1 + buy_foreign_medium_0
 - demand_medium_2 + inv_medium_2 - inv_medium_3 + unmet_medium_2 = 0
Inventory_Balance_medium_4: buy_canada_medium_2 + buy_foreign_medium_1
 - demand_medium_3 + inv_medium_3 - inv_medium_4 + unmet_medium_3 = 0
Inventory_Balance_medium_5: buy_canada_medium_3 + buy_foreign_medium_2
 - demand_medium_4 + inv_medium_4 - inv_medium_5 + unmet_medium_4 = 0
Inventory_Balance_medium_6: buy_canada_medium_4 + buy_foreign_medium_3
 - demand_medium_5 + inv_medium_5 - inv_medium_6 + unmet_medium_5 = 0
Max_Receive_1: buy_canada_heavy_0 + buy_canada_light_0 + buy_canada_medium_0
 + buy_domestic_heavy_0 + buy_domestic_light_0 + buy_domestic_medium_0
 + buy_foreign_heavy_0 + buy_foreign_light_0 + buy_foreign_medium_0 <= 31000
Max_Receive_2: buy_canada_heavy_1 + buy_canada_light_1 + buy_canada_medium_1
 + buy_domestic_heavy_1 + buy_domestic_light_1 + buy_domestic_medium_1
 + buy_foreign_heavy_1 + buy_foreign_light_1 + buy_foreign_medium_1 <= 28000
Max_Receive_3: buy_canada_heavy_2 + buy_canada_light_2 + buy_canada_medium_2
 + buy_domestic_heavy_2 + buy_domestic_light_2 + buy_domestic_medium_2
 + buy_foreign_heavy_2 + buy_foreign_light_2 + buy_foreign_medium_2 <= 31000
Max_Receive_4: buy_canada_heavy_3 + buy_canada_light_3 + buy_canada_medium_3
 + buy_domestic_heavy_3 + buy_domestic_light_3 + buy_domestic_medium_3
 + buy_foreign_heavy_3 + buy_foreign_light_3 + buy_foreign_medium_3 <= 30000
Max_Receive_5: buy_canada_heavy_4 + buy_canada_light_4 + buy_canada_medium_4
 + buy_domestic_heavy_4 + buy_domestic_light_4 + buy_domestic_medium_4
 + buy_foreign_heavy_4 + buy_foreign_light_4 + buy_foreign_medium_4 <= 31000
Max_Receive_6: buy_canada_heavy_5 + buy_canada_light_5 + buy_canada_medium_5
 + buy_domestic_heavy_5 + buy_domestic_light_5 + buy_domestic_medium_5
 + buy_foreign_heavy_5 + buy_foreign_light_5 + buy_foreign_medium_5 <= 30000
Min_Receive_3: buy_canada_heavy_2 + buy_canada_light_2 + buy_canada_medium_2
 + buy_domestic_heavy_2 + buy_domestic_light_2 + buy_domestic_medium_2
 + buy_foreign_heavy_2 + buy_foreign_light_2 + buy_foreign_medium_2 >= 1550
Min_Receive_4: buy_canada_heavy_3 + buy_canada_light_3 + buy_canada_medium_3
 + buy_domestic_heavy_3 + buy_domestic_light_3 + buy_domestic_medium_3
 + buy_foreign_heavy_3 + buy_foreign_light_3 + buy_foreign_medium_3 >= 1500
Min_Receive_5: buy_canada_heavy_4 + buy_canada_light_4 + buy_canada_medium_4
 + buy_domestic_heavy_4 + buy_domestic_light_4 + buy_domestic_medium_4
 + buy_foreign_heavy_4 + buy_foreign_light_4 + buy_foreign_medium_4 >= 1550
Min_Receive_6: buy_canada_heavy_5 + buy_canada_light_5 + buy_canada_medium_5
 + buy_domestic_heavy_5 + buy_domestic_light_5 + buy_domestic_medium_5
 + buy_foreign_heavy_5 + buy_foreign_light_5 + buy_foreign_medium_5 >= 1500
Bounds
 387.5 <= demand_heavy_0 <= 3875
 350 <= demand_heavy_1 <= 3500
 387.5 <= demand_heavy_2 <= 3875
 375 <= demand_heavy_3 <= 3750
 387.5 <= demand_heavy_4 <= 3875
 375 <= demand_heavy_5 <= 3750
 620 <= demand_light_0 <= 6200
 560 <= demand_light_1 <= 5600
 620 <= demand_light_2 <= 6200
 600 <= demand_light_3 <= 6000
 620 <= demand_light_4 <= 6200
 600 <= demand_light_5 <= 6000
 542.5 <= demand_medium_0 <= 5425
 490 <= demand_medium_1 <= 4900
 542.5 <= demand_medium_2 <= 5425
 525 <= demand_medium_3 <= 5250
 542.5 <= demand_medium_4 <= 5425
 525 <= demand_medium_5 <= 5250
 125 <= inv_heavy_0 <= 25000
 125 <= inv_heavy_1 <= 25000
 125 <= inv_heavy_2 <= 25000
 125 <= inv_heavy_3 <= 25000
 125 <= inv_heavy_4 <= 25000
 125 <= inv_heavy_5 <= 25000
 125 <= inv_heavy_6 <= 25000
 200 <= inv_light_0 <= 40000
 200 <= inv_light_1 <= 40000
 200 <= inv_light_2 <= 40000
 200 <= inv_light_3 <= 40000
 200 <= inv_light_4 <= 40000
 200 <= inv_light_5 <= 40000
 200 <= inv_light_6 <= 40000
 175 <= inv_medium_0 <= 35000
 175 <= inv_medium_1 <= 35000
 175 <= inv_medium_2 <= 35000
 175 <= inv_medium_3 <= 35000
 175 <= inv_medium_4 <= 35000
 175 <= inv_medium_5 <= 35000
 175 <= inv_medium_6 <= 35000
 unmet_heavy_0 <= 3875
 unmet_heavy_1 <= 3500
 unmet_heavy_2 <= 3875
 unmet_heavy_3 <= 3750
 unmet_heavy_4 <= 3875
 unmet_heavy_5 <= 3750
 unmet_light_0 <= 6200
 unmet_light_1 <= 5600
 unmet_light_2 <= 6200
 unmet_light_3 <= 6000
 unmet_light_4 <= 6200
 unmet_light_5 <= 6000
 unmet_medium_0 <= 5425
 unmet_medium_1 <= 4900
 unmet_medium_2 <= 5425
 unmet_medium_3 <= 5250
 unmet_medium_4 <= 5425
 unmet_medium_5 <= 5250
End
