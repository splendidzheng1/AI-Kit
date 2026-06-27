/*
 * @lc app=leetcode.cn id=443 lang=typescript
 *
 * [443] 压缩字符串
 */

// @lc code=start
function compress(chars: string[]): number {
    for (let i = 0; i < chars.length; i++) {
        let j = i;
        while (j < chars.length && chars[j] === chars[i]) {
            j++;
        }
        let num = j - i;
        if (num > 1) {
            let str = num.toString();
            chars.splice(i + 1, num - 1, ...str.split(''));
            i += str.length;
        }
    }
    return chars.length;
};
// @lc code=end

