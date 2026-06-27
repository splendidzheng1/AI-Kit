/*
 * @lc app=leetcode.cn id=1725 lang=typescript
 *
 * [1725] 可以形成最大正方形的矩形数目
 */

// @lc code=start
function countGoodRectangles(rectangles: number[][]): number {
    let max: number = 0;
    rectangles.forEach((item) => {
        max = Math.max(Math.min(...item), max);
    });

    let num: number = 0;    
    rectangles.forEach((item) => {
        if (Math.min(...item) === max) {
            num++;
        }
    });
    return num;
};
// @lc code=end

