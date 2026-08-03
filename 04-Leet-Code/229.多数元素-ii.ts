/*
 * @lc app=leetcode.cn id=229 lang=typescript
 *
 * [229] 多数元素 II
 */

// @lc code=start
function majorityElement(nums: number[]): number[] {
    if (nums.length === 0) return [];

    let candidate1: number | null = null;
    let candidate2: number | null = null;
    let count1 = 0;
    let count2 = 0;

    for (let num of nums) {
        if (candidate1 !== null && num === candidate1) {
            count1++;
        } else if (candidate2 !== null && num === candidate2) {
            count2++;
        } else if (count1 === 0) {
            candidate1 = num;
            count1 = 1;
        } else if (count2 === 0) {
            candidate2 = num;
            count2 = 1;
        } else {
            count1--;
            count2--;
        }
    }

    count1 = 0;
    count2 = 0;

    for (let num of nums) {
        if (num === candidate1) {
            count1++;
        } else if (num === candidate2) {
            count2++;
        }
    }

    const result: number[] = [];
    const n = nums.length;
    if (count1 > Math.floor(n / 3)) result.push(candidate1!);
    if (count2 > Math.floor(n / 3)) result.push(candidate2!);

    return result;
};
// @lc code=end

