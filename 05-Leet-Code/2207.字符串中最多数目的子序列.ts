/*
 * @lc app=leetcode.cn id=2207 lang=typescript
 *
 * [2207] 字符串中最多数目的子序列
 */

// @lc code=start
function maximumSubsequenceCount(text: string, pattern: string): number {
    let pre: number = 1;
    let countPre: number = 0;
    let suf: number = 0;
    let countSuf: number = 0;
    for (const c of text) {
        if (pattern[0] != pattern[1]) {
            if (c == pattern[0]) {
                pre += 1;
                suf += 1;
            }
            if (c == pattern[1]) {
                countPre += pre;
                countSuf += suf;
            }
        }
        else {
            if (c == pattern[0]) {
                countPre += pre;
                pre += 1;
            }
        }
    }
    return Math.max(countPre, countSuf + suf);
};
// @lc code=end

