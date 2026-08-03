
/*
 * @lc app=leetcode.cn id=3175 lang=typescript
 *
 * [3175] 找到连续赢 K 场比赛的第一位玩家
 */

// @lc code=start
function findWinningPlayer(skills: number[], k: number): number {
    const n = skills.length;
    let cnt = 0;
    let i = 0, last_i = 0;

    while (i < n) {
        let j = i + 1; 
        while (j < n && skills[j] < skills[i] && cnt < k) {
            j++;
            cnt++;
        }
        if (cnt === k) {
            return i;
        }
        cnt = 1;
        last_i = i;
        i = j;
    }
    return last_i;
};

// @lc code=end

