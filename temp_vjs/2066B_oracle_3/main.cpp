#include <bits/stdc++.h>
#define ll long long
#define endl '\n'
using namespace std;
 void solve()
{
 int n;
 cin >> n;
 int a[n + 5], sum = 0, mi = n + 1;
 for (int i = 1; i <= n; ++i){
  cin >> a[i];
  sum += a[i] == 0;
  if (a[i] == 0){
   mi = min(mi, i);
  }
 }
 vector < int > c;
 for (int i = 1; i <= n; ++i)
  if (a[i] || mi == i){
   c.push_back(a[i]);
  }
 auto check = [&](){
  set < int > s;
  int mex[n + 5];
  memset(mex, 0, sizeof(mex));
  for (int i = c.size() - 1; i >= 0; --i){
   s.insert(c[i]);
   mex[i] = mex[i + 1];
   while (s.count(mex[i])){
    ++mex[i];
   }
  }
  int x = 1e9;
  for (int i = 0; i < c.size(); ++i){
   x = min(x, c[i]);
   if (x < mex[i + 1]){
    return 0;
   }
  }
  return 1;
 };
 int ans = n - sum;
 if (sum && check()){
  ++ans;
 }
 cout << ans << endl;
}
 signed main()
{
 ios::sync_with_stdio(0);
 cin.tie(0);
 cout.tie(0);
 int T = 1;
 cin >> T;
 while (T--) solve();
 return 0;
}