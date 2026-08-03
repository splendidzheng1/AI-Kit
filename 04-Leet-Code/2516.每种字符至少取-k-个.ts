/*
 * @lc app=leetcode.cn id=2516 lang=typescript
 *
 * [2516] 每种字符至少取 K 个
 */

// @lc code=start
function takeCharacters(s: string, k: number): number {
    const cnt = [0, 0, 0];
    const len = s.length;
    let ans = len;

    for (let i = 0; i < len; i++) {
        cnt[s.charCodeAt(i) - 97]++;
    }
    if (cnt[0] >= k && cnt[1] >= k && cnt[2] >= k) {
        ans = Math.min(ans, len);
    } else {
        return -1;
    }

    let l = 0;
    for (let r = 0; r < len; r++) {
        cnt[s.charCodeAt(r) - 97]--;
        while (l < r && (cnt[0] < k || cnt[1] < k || cnt[2] < k)) {
            cnt[s.charCodeAt(l) - 97]++;
            l++;
        }
        if (cnt[0] >= k && cnt[1] >= k && cnt[2] >= k) {
            ans = Math.min(ans, len - (r - l + 1));
        }
    }

    return ans;
};
// @lc code=end

