/*
 * @lc app=leetcode.cn id=2750 lang=typescript
 *
 * [2750] 将数组划分成若干好子数组的方式
 */

// @lc code=start
function numberOfGoodSubarraySplits(nums: number[]): number {
    let zeroCount: number = 0;
    let totalCount: number = 0;
    for (const num of nums) {
        zeroCount++;
        if (num === 1) {
            totalCount = Math.max(totalCount * zeroCount, 1) % (Math.pow(10, 9) + 7);
            zeroCount = 0;
        }
    }

    return totalCount;
};
// @lc code=end

