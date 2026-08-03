/*
 * @lc app=leetcode.cn id=3148 lang=typescript
 *
 * [3148] 矩阵中的最大得分
 */

// @lc code=start
function maxScore(grid: number[][]): number {
    let max_score : number = Number.NEGATIVE_INFINITY;
    let row : number = grid.length;
    let col : number = grid[0].length;
    let dynamic_points : number[][] = Array.from({length: row}, () => Array(col).fill(0));
    for (let i = row - 1; i >= 0; i--) {
        for (let j = col - 1; j >= 0; j--) {
            if (i == row - 1 && j == col - 1) {
                continue;
            }
            let right_point = j + 1 < col ?
                Math.max(grid[i][j + 1] - grid[i][j], dynamic_points[i][j + 1] + (grid[i][j + 1] - grid[i][j]))
                 : Number.NEGATIVE_INFINITY;
            let down_point = i + 1 < row ?
                Math.max(grid[i + 1][j] - grid[i][j], dynamic_points[i + 1][j] + (grid[i + 1][j] - grid[i][j]))
                 : Number.NEGATIVE_INFINITY;
            dynamic_points[i][j] = Math.max(right_point, down_point);
            max_score = Math.max(max_score, dynamic_points[i][j]);
        }
    }
    return max_score;
};

// @lc code=end

