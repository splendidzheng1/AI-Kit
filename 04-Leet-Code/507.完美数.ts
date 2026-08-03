/*
 * @lc app=leetcode.cn id=507 lang=typescript
 *
 * [507] 完美数
 */

// @lc code=start
function checkPerfectNumber(num: number): boolean {
    if (num <= 1) return false;

    let sum: number = 1; // 初始化因子和为1
    for (let i = 2; i <= Math.sqrt(num); i++) {
        if (num % i === 0) {
            sum += i;
            if (i !== num / i) {
                sum += num / i;
            }
        }
    }

    return sum === num;
};
// @lc code=endhttps://fortune.com/company/jpmorgan-chase/
