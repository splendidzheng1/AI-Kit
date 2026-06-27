/*
 * @lc app=leetcode.cn id=2374 lang=typescript
 *
 * [2374] 边积分最高的节点
 */

// @lc code=start
function edgeScore(edges: number[]): number {
    let vertex: number[] = new Array(edges.length).fill(0);
    edges.forEach((edge, index) => {
        vertex[edge] += index;
    });
    return vertex.indexOf(Math.max(...vertex));
};
// @lc code=end

