/*
 * @lc app=leetcode.cn id=2535 lang=typescript
 *
 * [2535] 数组元素和与数字和的绝对差
 */

// @lc code=start
function differenceOfSum(nums: number[]): number {
    // 计算数组元素的和
    const elementSum = nums.reduce((acc, curr) => acc + curr, 0);

    // 计算数组中每个数字的每一位的和
    const digitSum = nums
        .join('') // 将数组转换为字符串
        .split('') // 将字符串按每个字符分割成数组
        .map(Number) // 将每个字符转换为数字
        .reduce((acc, digit) => acc + digit, 0); // 计算每一位数字的和

    // 返回两者的绝对差
    return Math.abs(elementSum - digitSum);
}
// @lc code=end

