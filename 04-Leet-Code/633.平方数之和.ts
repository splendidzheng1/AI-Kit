/*
 * @lc app=leetcode.cn id=633 lang=typescript
 *
 * [633] 平方数之和
 */

// @lc code=start
function judgeSquareSum(c: number): boolean {
    for (let a = 0; a * a <= c; a++) {
        const b = Math.sqrt(c - a * a);
        if (b === parseInt(b.toString())) {
            return true;
        }
    }
    return false;
};
// @lc code=end

