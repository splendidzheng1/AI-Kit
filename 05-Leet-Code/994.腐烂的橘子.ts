/*
 * @lc app=leetcode.cn id=994 lang=typescript
 *
 * [994] 腐烂的橘子
 */

// @lc code=start
function orangesRotting(grid: number[][]): number {
    let positions: number[][] = []; // 用于记录行列值的数组

    for (let i = 0; i < grid.length; i++) {
        for (let j = 0; j < grid[i].length; j++) {
            if (grid[i][j] === 2) {
                positions.push([i, j]); // 记录行列值
            }
        }
    }

    if (!hasFreshOranges(grid)) {
        return 0; // 如果没有新鲜橘子，直接返回0
    }

    let minutes = 0;
    while (positions.length > 0) {
        let newPositions: number[][] = [];
        for (let position of positions) {
            let i = position[0];
            let j = position[1];
            if (i > 0 && grid[i - 1][j] === 1) {
                grid[i - 1][j] = 2;
                newPositions.push([i - 1, j]);
            }
            if (i < grid.length - 1 && grid[i + 1][j] === 1) {
                grid[i + 1][j] = 2;
                newPositions.push([i + 1, j]);
            }
            if (j > 0 && grid[i][j - 1] === 1) {
                grid[i][j - 1] = 2;
                newPositions.push([i, j - 1]);
            }
            if (j < grid[i].length - 1 && grid[i][j + 1] === 1) {
                grid[i][j + 1] = 2;
                newPositions.push([i, j + 1]);
            }
        }
        if (newPositions.length === 0) {
            break; // 如果没有新的腐烂橘子，跳出循环
        }
        positions = newPositions;
        minutes++;
    }

    return hasFreshOranges(grid) ? -1 : minutes; // 如果还有新鲜橘子，返回-1，否则返回分钟数
}

function hasFreshOranges(grid: number[][]): boolean {
    for (let i = 0; i < grid.length; i++) {
        for (let j = 0; j < grid[i].length; j++) {
            if (grid[i][j] === 1) {
                return true; // 如果找到值为1的元素，返回true
            }
        }
    }
    return false; // 如果没有找到值为1的元素，返回false
}
// @lc code=end
