#include <algorithm>
#include <array>
#include <bitset>
#include <cassert>
#include <charconv>
#include <cstring>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <optional>
#include <random>
#include <set>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>
#include <unordered_map>
#include <utility>
#include <variant>
#include <vector>
#include <queue>
using namespace std;
 void solve() {
    int n;
    cin >> n;
     vector<int> a(n);
    vector<vector<int>> ind(n + 1);
     for (int i = 0; i < n; i++) {
        cin >> a[i];
         if (a[i] <= n) {
            ind[a[i]].push_back(i);
        }
    }
     if (ind[0].empty()) {
        cout << n << endl;
        return;
    }
     int x = ind[0][0];
    int rest = n - (int) ind[0].size();
     int ans = max(1, rest);
     for (int m = 1; m <= n; m++) {
        if (ind[m].empty()) {
            ans = max(ans, n + 1 - (int) ind[0].size());
            cout << ans << endl;
            return;
        }
        else {
            int y = upper_bound(ind[m].begin(), ind[m].end(), x) - ind[m].begin();
            int left = y;
            int right = ((int) ind[m].size()) - y;
             if ((left > 0 && right > 0) || (left > 1)) {
                cout << ans << endl;
                return;
            }
            else if (left == 1) {
                x = ind[m][0];
            }
            else if (right > 0) {
                            }
        }
    }
     cout << ans << endl;
}
 int main() {
    cin.tie(0);
    ios_base::sync_with_stdio(0);
     int t;
    cin >> t;
     while (t--) {
        solve();
    }
}