/*
 * @lc app=leetcode.cn id=3275 lang=cpp
 *
 * [3275] 第 K 近障碍物查询（最大堆）
 */

// @lc code=start
class Solution {
    public:
        vector<int> resultsArray(vector<vector<int>>& queries, int k) {
            vector<int> ans(queries.size(), -1);
            priority_queue<int> pq;
            for (int i = 0; i < queries.size(); i++) {
                pq.push(abs(queries[i][0]) + abs(queries[i][1]));
                if (pq.size() > k) {
                    pq.pop();
                }
                if (pq.size() == k) {
                    ans[i] = pq.top();
                }
            }
            return ans;
        }
};
// @lc code=end

