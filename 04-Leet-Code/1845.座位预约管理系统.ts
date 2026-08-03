/*
 * @lc app=leetcode.cn id=1845 lang=typescript
 *
 * [1845] 座位预约管理系统（最小堆）
 */

// @lc code=start
class SeatManager {
    private available;

    constructor(n: number) {
        this.available = new MinPriorityQueue();
        for (let i = 1; i <= n; i++) {
            this.available.enqueue(i, i);
        }
    }

    reserve(): number {
        return this.available.dequeue().element;
    }

    unreserve(seatNumber: number): void {
        this.available.enqueue(seatNumber);
    }
}

/**
 * Your SeatManager object will be instantiated and called as such:
 * var obj = new SeatManager(n)
 * var param_1 = obj.reserve()
 * obj.unreserve(seatNumber)
 */
// @lc code=end

