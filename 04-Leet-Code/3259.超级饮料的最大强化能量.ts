/*
 * @lc app=leetcode.cn id=3259 lang=typescript
 *
 * [3259] 超级饮料的最大强化能量
 */

// @lc code=start
function maxEnergyBoost(energyDrinkA: number[], energyDrinkB: number[]): number {
    let dpA1 = energyDrinkA[0];
    let dpB1 = energyDrinkB[0];
    let dpA2 = dpA1 + energyDrinkA[1];
    let dpB2 = dpB1 + energyDrinkB[1];
    for (let i = 2; i < energyDrinkA.length; i++) {
        let _dpA2 = Math.max(dpA2 + energyDrinkA[i], dpB1 + energyDrinkA[i]);
        let _dpB2 = Math.max(dpB2 + energyDrinkB[i], dpA1 + energyDrinkB[i]);
        dpA1 = dpA2;
        dpB1 = dpB2;
        dpA2 = _dpA2;
        dpB2 = _dpB2;
    }
    return Math.max(dpA2, dpB2);
};
// @lc code=end

