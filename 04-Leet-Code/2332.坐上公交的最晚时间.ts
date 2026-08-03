/*
 * @lc app=leetcode.cn id=2332 lang=typescript
 *
 * [2332] 坐上公交的最晚时间
 */

// @lc code=start
function latestTimeCatchTheBus(buses: number[], passengers: number[], capacity: number): number {
    buses.sort((a, b) => a - b);
    passengers.sort((a, b) => a - b);
    let pos = 0;
    let space = 0;

    for (const arrive of buses) {
        space = capacity;
        while (space > 0 && pos < passengers.length && passengers[pos] <= arrive) {
            space--;
            pos++;
        }
    }

    pos--;
    let lastCatchTime = space > 0 ? buses[buses.length - 1] : passengers[pos];
    while (pos >= 0 && passengers[pos] === lastCatchTime) {
        pos--;
        lastCatchTime--;
    }

    return lastCatchTime;
}
// @lc code=end

