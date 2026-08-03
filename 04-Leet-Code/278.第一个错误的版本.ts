/*
 * @lc app=leetcode.cn id=278 lang=typescript
 *
 * [278] 第一个错误的版本
 */

// @lc code=start
/**
 * The knows API is defined in the parent class Relation.
 * isBadVersion(version: number): boolean {
 *     ...
 * };
 */

var solution = function(isBadVersion: any) {

    return function(n: number): number {
        let mid : number = Math.ceil(n / 2);
        while (!isBadVersion(mid)) {
            mid = mid + Math.ceil((n - mid) / 2);
        }
        while (isBadVersion(mid - 1)) {
            mid--;
        }
        return mid;
    };
};

// @lc code=end

