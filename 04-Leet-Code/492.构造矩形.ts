/*
 * @lc app=leetcode.cn id=492 lang=typescript
 *
 * [492] 构造矩形
 */

// @lc code=start
function constructRectangle(area: number): number[] {
    let w = Math.floor(Math.sqrt(area));
    while (area % w != 0) {
        w--;
    }
    return [area / w, w];
};
// @lc code=end

