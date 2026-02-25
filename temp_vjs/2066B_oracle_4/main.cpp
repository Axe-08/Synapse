#include <bits/stdc++.h>
#include <ext/pb_ds/assoc_container.hpp>
#include <ext/pb_ds/tree_policy.hpp>
using namespace std;
 // Debug template begins ------------------------------------------------------------------------------------------------------------------
#define debug(...) cerr << "[" << #__VA_ARGS__ << "] = ", _print(__VA_ARGS__), cerr << endl;
 void _print() {}
 void _print(int t) { cerr << t; }
void _print(long t) { cerr << t; }
void _print(long long t) { cerr << t; }
void _print(unsigned t) { cerr << t; }
void _print(unsigned long t) { cerr << t; }
void _print(unsigned long long t) { cerr << t; }
void _print(float t) { cerr << t; }
void _print(double t) { cerr << t; }
void _print(long double t) { cerr << t; }
void _print(char t) { cerr << '\'' << t << '\''; }
void _print(const char *t) { cerr << '\"' << t << '\"'; }
void _print(string t) { cerr << '\"' << t << '\"'; }
void _print(bool t) { cerr << (t ? "true" : "false"); }
 template <typename T, typename V> void _print(pair<T, V> p) { cerr << "{"; _print(p.first); cerr << ", "; _print(p.second); cerr << "}"; }
template <typename T> void _print(vector<T> v) { cerr << "["; for (auto &i : v) _print(i), cerr << " "; cerr << "]"; }
template <typename T> void _print(list<T> v) { cerr << "["; for (auto &i : v) _print(i), cerr << " "; cerr << "]"; }
template <typename T> void _print(deque<T> v) { cerr << "["; for (auto &i : v) _print(i), cerr << " "; cerr << "]"; }
template <typename T> void _print(set<T> v) { cerr << "{"; for (auto &i : v) _print(i), cerr << " "; cerr << "}"; }
template <typename T> void _print(unordered_set<T> v) { cerr << "{"; for (auto &i : v) _print(i), cerr << " "; cerr << "}"; }
template <typename T> void _print(multiset<T> v) { cerr << "{"; for (auto &i : v) _print(i), cerr << " "; cerr << "}"; }
template <typename T> void _print(stack<T> v) { vector<T> temp; while (!v.empty()) temp.push_back(v.top()), v.pop(); reverse(temp.begin(), temp.end()); _print(temp); }
template <typename T> void _print(queue<T> v) { vector<T> temp; while (!v.empty()) temp.push_back(v.front()), v.pop(); _print(temp); }
template <typename T> void _print(priority_queue<T> v) { vector<T> temp; while (!v.empty()) temp.push_back(v.top()), v.pop(); _print(temp); }
template <typename T> void _print(priority_queue<T, vector<T>, greater<T>> v) { vector<T> temp; while (!v.empty()) temp.push_back(v.top()), v.pop(); _print(temp); }
 template <typename T, typename V> void _print(map<T, V> v) { cerr << "{"; for (auto &i : v) _print(i), cerr << " "; cerr << "}"; }
template <typename T, typename V> void _print(unordered_map<T, V> v) { cerr << "{"; for (auto &i : v) _print(i), cerr << " "; cerr << "}"; }
 template <typename T> void _print(T *arr, int size) { cerr << "["; for (int i = 0; i < size; ++i) _print(arr[i]), cerr << " "; cerr << "]"; }
 template <typename T, typename... Args> void _print(T t, Args... args) { _print(t); cerr << ", "; _print(args...); }
// Debug template ends --------------------------------------------------------------------------------------------------------------------
 mt19937_64 RNG(chrono::steady_clock::now().time_since_epoch().count());
typedef __gnu_pbds::tree<int, __gnu_pbds::null_type, less<int>, __gnu_pbds::rb_tree_tag, __gnu_pbds::tree_order_statistics_node_update> ordered_set;
 #define int long long
#define rep(i, x, n) for (int i = x; i < n; i++)
#define rrep(i, x, n) for (int i = n; i >= x; i--)
#define all(x) (x).begin(), (x).end()
#define fi first
#define se second
#define endl "\n"
#define pb push_back
#define pii pair<int, int>
#define vi vector<int>
#define vii vector<pair<int,int>>
#define vvi vector<vector<int>>
#define inf (int)1e18
 const int M=1e9+7;
const int M2=998244353;
 // Binary Exponentiation
int binExp(int a, int b) { int x = 1; while (b) { if (b & 1) x = (x * 1ll * a) % M; a = (a * 1ll * a) % M; b >>= 1; } return x; }
 void Solve()
{
    int n;
    cin>>n;
    int z=-1;
    vi a(n);
    rep(i,0,n) cin>>a[i];
    vi b;
    rep(i,0,n){
        if(a[i]>0) b.pb(a[i]);
        else if(z==-1){
            b.pb(a[i]);
            z=i;
        }
    }
    n=b.size();
    vi mi(n);
    mi[0]=b[0];
    rep(i,1,n){
        mi[i]=min(mi[i-1],b[i]);
    }
    set<int>missing;
    rep(i,0,n+1) missing.insert(i);
    rrep(i,1,n-1){
        if(missing.count(b[i])){
            missing.erase(b[i]);
        }
        if(mi[i-1]<*missing.begin()){
            cout<<n-1<<endl;
            return;
        }
    }
    cout<<n<<endl;
}
 int32_t main()
{
    auto begin = std::chrono::high_resolution_clock::now();
    ios_base::sync_with_stdio(0);
    cin.tie(0);
    int t = 1;
    // freopen("in",  "r", stdin);
    // freopen("out", "w", stdout);
        cin >> t;
    while(t--)
    {
        //cout << "Case #" << i << ": ";
        Solve();
    }
    auto end = std::chrono::high_resolution_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::nanoseconds>(end - begin);
    // cerr << "Time measured: " << elapsed.count() * 1e-9 << " seconds.\n"; 
    return 0;
}