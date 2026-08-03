/*
 * @lc app=leetcode.cn id=3184 lang=typescript
 *
 * [3184] 构成整天的下标对数目 I
 */

// @lc code=start
function countCompleteDayPairs(hours: number[]): number {
    let res: number = 0;
    for (let i = 0; i < hours.length; i++) {
        for (let j = i + 1; j < hours.length; j++) {
            if ((hours[i] + hours[j]) % 24 === 0) {
                res++;
            }
        }
    }
    return res;
};
// @lc code=end

