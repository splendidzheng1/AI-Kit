/*
 * @lc app=leetcode.cn id=2000 lang=typescript
 *
 * [2000] 反转单词前缀
 */

// @lc code=start
function reversePrefix(word: string, ch: string): string {
    const index = word.indexOf(ch);
    if (index >= 0) {
        const arr = [...word.slice(0, index + 1)];
        word = arr.reverse().join('') + word.slice(index + 1);
    }
    return word;
};
// @lc code=end

