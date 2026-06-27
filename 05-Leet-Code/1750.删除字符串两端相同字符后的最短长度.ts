/*
 * @lc app=leetcode.cn id=1750 lang=typescript
 *
 * [1750] 删除字符串两端相同字符后的最短长度
 */

// @lc code=start
function minimumLength(s: string): number {
    let left:number = 0;
    let right:number = s.length - 1;
    while (left < right) {
        if (s[left] != s[right]) {
            break;
        }
        let ch:string = s[left];
        while (left <= right && s[left] == ch) {
            left++;
        }
        while (left <= right && s[right] == ch) {
            right--;
        }
    }
    return right - left + 1;
};
// @lc code=end

