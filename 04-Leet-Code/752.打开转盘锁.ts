/*
 * @lc app=leetcode.cn id=752 lang=typescript
 *
 * [752] 打开转盘锁（广度优先搜索）
 */

// @lc code=start
function openLock(deadends: string[], target: string): number {
    const plusOne = (code: string, pos: number): string => {
        const arr = code.split('');
        if (arr[pos] === '9') {
            arr[pos] = '0';
        } else {
            arr[pos] = (parseInt(arr[pos]) + 1).toString();
        }
        return arr.join('');
    };

    const minusOne = (code: string, pos: number): string => {
        const arr = code.split('');
        if (arr[pos] === '0') {
            arr[pos] = '9';
        } else {
            arr[pos] = (parseInt(arr[pos]) - 1).toString();
        }
        return arr.join('');
    }
    const deadSet = new Set(deadends);
    if (deadSet.has('0000')) {
        return -1;
    }

    const queue: string[] = [];
    queue.push('0000');
    const visited = new Set();
    visited.add('0000');

    let step = 0;

    while (queue.length) {
        const size = queue.length;
        for (let i = 0; i < size; i++) {
            const cur = queue.shift() as string;
            if (cur === target) {
                return step;
            }

            for (let j = 0; j < 4; j++) {
                const up = plusOne(cur, j);
                if (!visited.has(up) && !deadSet.has(up)) {
                    queue.push(up);
                    visited.add(up);
                }

                const down = minusOne(cur, j);
                if (!visited.has(down) && !deadSet.has(down)) {
                    queue.push(down);
                    visited.add(down);
                }
            }
        }
        step++;
    }

    return -1;

};
// @lc code=end

