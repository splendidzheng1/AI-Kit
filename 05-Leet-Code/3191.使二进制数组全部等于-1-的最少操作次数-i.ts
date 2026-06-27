/*
 * @lc app=leetcode.cn id=3191 lang=typescript
 *
 * [3191] 使二进制数组全部等于 1 的最少操作次数 I
 */

// @lc code=start
function minOperations(nums: number[]): number {
    const n = nums.length;
    let ans = 0;
    for (let i = 0; i < n - 2; i++) {
        if (nums[i] === 0) { // 必须操作
            nums[i + 1] ^= 1;
            nums[i + 2] ^= 1;
            ans++;
        }
    }
    return nums[n - 2] && nums[n - 1] ? ans : -1;
};
// @lc code=end

