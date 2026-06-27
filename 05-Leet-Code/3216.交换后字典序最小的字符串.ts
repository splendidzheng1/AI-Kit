/*
 * @lc app=leetcode.cn id=3216 lang=typescript
 *
 * [3216] 交换后字典序最小的字符串
 */

// @lc code=start
function getSmallestString(s: string): string {
    let sArray = s.split('');
    let length = sArray.length;
    for (let i = 0; i < length - 1; i++) {
        let pre = Number(sArray[i]);
        let last = Number(sArray[i + 1]);
        if ((pre % 2) === (last % 2) && pre > last) {
            [sArray[i], sArray[i + 1]] = [sArray[i + 1], sArray[i]];
            break;
        }
    }
    return sArray.join('');
};
// @lc code=end

