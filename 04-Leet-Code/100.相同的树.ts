/*
 * @lc app=leetcode.cn id=100 lang=typescript
 *
 * [100] 相同的树
 */

// @lc code=start
/**
 * Definition for a binary tree node.
 * class TreeNode {
 *     val: number
 *     left: TreeNode | null
 *     right: TreeNode | null
 *     constructor(val?: number, left?: TreeNode | null, right?: TreeNode | null) {
 *         this.val = (val===undefined ? 0 : val)
 *         this.left = (left===undefined ? null : left)
 *         this.right = (right===undefined ? null : right)
 *     }
 * }
 */

function isSameTree(p: TreeNode | null, q: TreeNode | null): boolean {
    let pStack: TreeNode[] = [];
    let qStack: TreeNode[] = [];
    pStack.push(p);
    qStack.push(q);
    while (pStack.length && qStack.length) {
        let p = pStack.pop();
        let q = qStack.pop();
        if (p === null && q === null) {
            continue;
        }
        if (p === null || q === null) {
            return false;
        }
        if (p.val !== q.val) {
            return false;
        }
        pStack.push(p.left);
        pStack.push(p.right);
        qStack.push(q.left);
        qStack.push(q.right);
    }
    return true;
};
// @lc code=end

