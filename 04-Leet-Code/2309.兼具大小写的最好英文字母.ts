/*
 * @lc app=leetcode.cn id=2309 lang=typescript
 *
 * [2309] 兼具大小写的最好英文字母
 */

// @lc code=start
function greatestLetter(s: string): string {
    let uppercase: boolean[] = new Array(26).fill(false);
    let lowercase: boolean[] = new Array(26).fill(false);

    for (let c of s) {
        let asciiCode = c.charCodeAt(0);
        if (asciiCode >= 65 && asciiCode <= 90) {
            // 大写字母
            uppercase[asciiCode - 65] = true;
        } else if (asciiCode >= 97 && asciiCode <= 122) {
            // 小写字母
            lowercase[asciiCode - 97] = true;
        }
    }

    for (let i = 25; i >= 0; i--) {
        if (uppercase[i] && lowercase[i]) {
            return String.fromCharCode(i + 65);
        }
    }

    return '';
};
// @lc code=end

