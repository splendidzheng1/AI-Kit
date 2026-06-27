/*
 * @lc app=leetcode.cn id=2 lang=typescript
 *
 * [2] 两数相加
 */

// @lc code=start
/**
 * Definition for singly-linked list.
 * class ListNode {
 *     val: number
 *     next: ListNode | null
 *     constructor(val?: number, next?: ListNode | null) {
 *         this.val = (val===undefined ? 0 : val)
 *         this.next = (next===undefined ? null : next)
 *     }
 * }
 */

function addTwoNumbers(l1: ListNode | null, l2: ListNode | null): ListNode | null {
    const res = new ListNode(0);
    var head = res;
    do
    {
        var val = (l1 != null ? l1.val : 0) + (l2 != null ? l2.val : 0) + head.val;
        head.val = val % 10;
        var carry = val >= 10 ? 1 : 0;
        if ((l1 != null && l1.next != null) || (l2 != null && l2.next != null) || carry > 0)
        {
            head.next = new ListNode(carry);
            head = head.next;
        }
        l1 = l1 == null ? null : l1.next;
        l2 = l2 == null ? null : l2.next;
    }
    while(l1 != null || l2 != null); 
    return res;
};
// @lc code=end