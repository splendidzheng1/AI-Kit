/*
 * @lc app=leetcode.cn id=1014 lang=typescript
 *
 * [1014] 最佳观光组合
 */

// @lc code=start
function maxScoreSightseeingPair(values: number[]): number {
    let maxScore = 0;
    let maxI = values[0] + 0; // values[i] + i

    for (let j = 1; j < values.length; j++) {
        maxScore = Math.max(maxScore, maxI + values[j] - j); // values[i] + values[j] + i - j
        maxI = Math.max(maxI, values[j] + j); // 更新 maxI
    }

    return maxScore;
};
// @lc code=end

