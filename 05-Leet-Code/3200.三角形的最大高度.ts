/*
 * @lc app=leetcode.cn id=3200 lang=typescript
 *
 * [3200] 三角形的最大高度
 */

// @lc code=start
function maxHeightOfTriangle(red: number, blue: number): number {
    let [red1, red2] = [red, red];
    let [blue1, blue2] = [blue, blue];
    let level1 = 0;
    let level2 = 0;
    red1 -= 1;
    blue1 -= 2;
    while (true) {
        if (red1 >= 0) {
            level1++;
            red1 -= 1 + (Math.floor((level1 + 1) / 2)) * 2;
            if (blue1 >= 0) {
                level1++;
                blue1 -= 2 + (Math.floor((level1 + 1) / 2)) * 2;
            } else {
                break;
            }
        } else {
            break;
        }
    }
    blue2 -= 1;
    red2 -= 2;
    while (true) {
        if (blue2 >= 0) {
            level2++;
            blue2 -= 1 + (Math.floor((level2 + 1) / 2)) * 2;
            if (red2 >= 0) {
                level2++;
                red2 -= 2 + (Math.floor((level2 + 1) / 2)) * 2;
            } else {
                break;
            }
        } else {
            break;
        }
    }
    return Math.max(level1, level2);
};
// @lc code=end

