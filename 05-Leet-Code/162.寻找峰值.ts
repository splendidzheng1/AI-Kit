/*
 * @lc app=leetcode.cn id=162 lang=typescript
 *
 * [162] 寻找峰值
 */

// @lc code=start
function findPeakElement(nums: number[]): number {
    let left:number = 0;
    let right:number = nums.length - 1;
    while (left < right)
    {
        let mid:number = Math.floor((left + right) / 2);
        let res:number = compare(nums, mid);
        if (res == 0) {
            return mid;
        }
        else if (res == 1) {
            left = mid + 1;
        }
        else {
            right = mid - 1;
        }
    }
    return left;
};

function compare(nums:number[], order:number): number {
    if (order == 0) {
        if (nums[order] > nums[order + 1]) {
            return 0;
        }
        else {
            return 1;
        }
    }
    if (nums[order] > nums[order - 1] && nums[order] > nums[order + 1]) {
        return 0;
    }
    if (nums[order] > nums[order -1]) {
        return 1;
    }
    else {
        return -1;
    }
}

// @lc code=end

