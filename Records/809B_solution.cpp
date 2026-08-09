#include <bits/stdc++.h>

using namespace std;

bool query(int x, int y) {
  cout << "1 " << x << " " << y << endl;
  cout.flush();
  string response;
  cin >> response;
  return response == "TAK";
}

int find_an_ordered_dish(int low, int high) {
  while (low < high) {
    int mid = low + (high - low) / 2;
    if (query(mid, mid + 1)) {
      high = mid;
    } else {
      low = mid + 1;
    }
  }
  return low;
}

int main() {
  ios_base::sync_with_stdio(false);
  cin.tie(NULL);

  int n, k;
  cin >> n >> k;

  int first_dish = find_an_ordered_dish(1, n);
  int second_dish = -1;

  if (first_dish > 1) {
    int left_search_low = 1;
    int left_search_high = first_dish - 1;
    while (left_search_low < left_search_high) {
      int mid = left_search_low + (left_search_high - left_search_low) / 2;
      if (mid + 1 < first_dish) {
        if (query(mid, mid + 1)) {
          left_search_high = mid;
        } else {
          left_search_low = mid + 1;
        }
      } else {
        if (query(mid, first_dish)) {
          left_search_high = mid;
        } else {
          left_search_low = mid + 1;
        }
      }
    }
    if (left_search_low < first_dish && query(left_search_low, first_dish)) {
      second_dish = left_search_low;
    }
  }

  if (second_dish == -1) {
    int right_search_low = first_dish + 1;
    int right_search_high = n;
    while (right_search_low < right_search_high) {
      int mid = right_search_low + (right_search_high - right_search_low) / 2;
      if (query(mid + 1, mid)) {
        right_search_low = mid + 1;
      } else {
        right_search_high = mid;
      }
    }
    second_dish = right_search_low;
  }

  cout << "2 " << first_dish << " " << second_dish << endl;
  cout.flush();

  return 0;
}