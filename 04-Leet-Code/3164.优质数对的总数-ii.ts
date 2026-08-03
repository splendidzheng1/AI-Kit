/*
 * @lc app=leetcode.cn id=3164 lang=typescript
 *
 * [3164] 优质数对的总数 II
 */

// @lc code=start
function numberOfPairs(nums1: number[], nums2: number[], k: number): number {
    let n: number = 0;
    if (nums1.length === 0 || nums2.length === 0) {
        return n;
    }

    nums2 = nums2.map((num) => num * k);
    nums1.forEach((num1) => {
        n += nums2.filter((num2) => num1 % num2 === 0).length;
    });
    return n;
};
// @lc code=end

