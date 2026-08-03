/*
 * @lc app=leetcode.cn id=2073 lang=typescript
 *
 * [2073] 买票需要的时间
 */

// @lc code=start
function timeRequiredToBuy(tickets: number[], k: number): number {
    let time: number = 0;
    while (tickets[k] > 0) {
        tickets[0]--;
        time += tickets[0] < 0 ? 0 : 1;
        tickets.push(tickets.shift() as number);
        k = k - 1 < 0 ? tickets.length - 1 : k - 1;
    }

    return time;
};
// @lc code=end

