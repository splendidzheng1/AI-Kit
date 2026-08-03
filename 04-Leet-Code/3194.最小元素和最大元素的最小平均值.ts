/*
 * @lc app=leetcode.cn id=3194 lang=typescript
 *
 * [3194] 最小元素和最大元素的最小平均值
 */

// @lc code=start
function minimumAverage(nums: number[]): number {
    nums.sort((a, b) => a - b);
    let min: number = Number.MAX_SAFE_INTEGER;
    for(let i = 0; i < nums.length / 2; i++) {
        min = Math.min(min, (nums[i] + nums[nums.length - i - 1])/ 2)
    }

    return min;
};
// @lc code=end

