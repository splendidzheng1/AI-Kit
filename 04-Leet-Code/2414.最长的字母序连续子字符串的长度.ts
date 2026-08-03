/*
 * @lc app=leetcode.cn id=2414 lang=typescript
 *
 * [2414] 最长的字母序连续子字符串的长度
 */

// @lc code=start
function longestContinuousSubstring(s: string): number {
    if (s.length === 0) {
        return 0;
    }

    let continuous: number = 1;
    let record: number = 1;
    for (let i = 1; i < s.length; i++) {
        if (s.charCodeAt(i) - s.charCodeAt(i - 1) === 1) {
            record++;
        } else {
            continuous = Math.max(continuous, record);  
            record = 1;
        }
    }

    return Math.max(continuous, record);
};
// @lc code=end

