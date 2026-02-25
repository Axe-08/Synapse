#include <iostream>
#include <assert.h>
#include <cmath>
#include <iomanip> 
#include <algorithm>
#include <numeric>
#include <vector>
#include <map>
#include <set>
#include <queue>
#define int long long
#define pb push_back
#define fwd(i,a,b) for(int i=a;i<b ;i++)
#define double long double 
#define take(n)  int n=0; cin>>n 
#define take2(n,m) int n,m ; cin>>n>>m ;
#define sortt(v) sort(v.begin(),v.end()) ;
#define Itarr(n)  int arr[n] ; fwd(i,0,n){cin>>arr[i];}
#define Itarrx(x,m) int x[m] ; fwd(i,0,m){cin>>x[i];}   
#define Iv(v,n) vector<int>v(n,0) ; fwd(i,0,n){cin>>v[i] ;} ;
#define set_tox(arr,n,x) fwd(i,0,n){arr[i]=x;}
#define pb push_back
#define take_graph(n,m) vector<vector<int>> g(n,vector<int>()) ;int a,b ; fwd(i,0,m){cin>>a>>b ;a-- ;b-- ;g[a].pb(b) ; g[b].pb(a) ; }
#define take_graph_dir(n,m) vector<vector<int>> g(n,vector<int>()) ;int a,b ; fwd(i,0,m){cin>>a>>b ;a-- ;b-- ;g[a].pb(b) ; }
#define endl "\n"
#define what_is(x) cout<< #x << " is " << x << endl;
#define check(arr,n)             fwd(i,0,n){cout<<arr[i]<<' ' ;} cout<<endl ;
const int INF= 1e18 ;
int tt ; 
using namespace std; 
const int MOD=998244353;
#define m_p(a,b) make_pair(a,b) 
#define MAXN 400005
 /*---------struct here ----------*/
int euclid(int a, int b, int &x, int &y) {
    if (!b) return x = 1, y = 0, a;
    int d = euclid(b, a % b, y, x);
    return y -= a/b * x, d;
}
 const int mod = 998244353;
struct mint {
    int x;
    mint(int xx) : x(xx) {}
    mint operator+(mint b) { return mint((x + b.x) % mod); }
    mint operator-(mint b) { return mint((x - b.x + mod) % mod); }
    mint operator*(mint b) { return mint((x * b.x) % mod); }
    mint operator/(mint b) { return *this * invert(b); }
    mint invert(mint a) {
        int x, y, g = euclid(a.x, mod, x, y);
        assert(g == 1); return mint((x + mod) % mod);
    }
    mint operator^(int e) {
        if (!e) return mint(1);
        mint r = *this ^ (e / 2); r = r * r;
        return e&1 ? *this * r : r;
    }
};
        /*-------functions below -------------------------------------*/
bool is_prime(int n){
    int i=2 ; 
    while(i*i<=n){
        ++i ; 
        if (n%i==0) return false  ;
    }
    return true  ;
}
   vector<int> spf(MAXN + 1, 1);
 // Calculating SPF (Smallest Prime Factor) for every
// number till MAXN.
// Time Complexity : O(nloglogn)
void sieve()
{
    // stores smallest prime factor for every number
     spf[0] = 0;
    for (int i = 2; i <= MAXN; i++) {
        if (spf[i] == 1) { // if the number is prime ,mark
                           // all its multiples who havent
                           // gotten their spf yet
            for (int j = i; j <= MAXN; j += i) {
                if (spf[j]== 1) // if its smallest prime factor is
                          // 1 means its spf hasnt been
                          // found yet so change it to i
                    spf[j] = i;
            }
        }
    }
}
 // A O(log n) function returning primefactorization
// by dividing by smallest prime factor at every step
vector<int> getFactorization(int x)
{
    vector<int> ret;
    while (x != 1) {
        ret.push_back(spf[x]);
        x = x / spf[x];
    }
    return ret;
}
 // driver
 int binexp(int a,int n,int mod)
{
    if(n==0) return 1;
     else if(a==0 && n!=0) return 0;
     else
    {
        int z=binexp(a,n/2,mod);
        int y=(z*z)%mod;
         if(n&1) return (a*y)%mod;
        else return y%mod;
    }
}
  int getGCD(int a, int b){
    if (a==0 && b==0) return 0 ;
    else if (a==0) return b  ;
    else if (b==0) return a ;
    else {
        if (a>=b) return getGCD(b,a%b) ;
        else return getGCD(a,b%a) ;
}}
int getLCM(int a , int b){
    if (a==0 || b==0) return 0 ; 
    else return (a*b)/getGCD(a,b) ;
 }
    int findXOR(int n)
{
    int mod = n % 4;
     // If n is a multiple of 4
    if (mod == 0)
        return n;
     // If n % 4 gives remainder 1
    else if (mod == 1)
        return 1;
     // If n % 4 gives remainder 2
    else if (mod == 2)
        return n + 1;
     // If n % 4 gives remainder 3
    else if (mod == 3)
        return 0;
}
 // Function to return the XOR of elements
// from the range [l, r]
int findXOR(int l, int r)
{
    return (findXOR(l - 1) ^ findXOR(r));
}
 int countAndMerge(vector<int>& arr, int l, int m, int r) {
      // Counts in two subarrays
    int n1 = m - l + 1, n2 = r - m;
     // Set up two vectors for left and right halves
    vector<int> left(n1), right(n2);
    for (int i = 0; i < n1; i++)
        left[i] = arr[i + l];
    for (int j = 0; j < n2; j++)
        right[j] = arr[m + 1 + j];
     // Initialize inversion count (or result) and merge two halves
    int res = 0;
    int i = 0, j = 0, k = l;
    while (i < n1 && j < n2) {
         // No increment in inversion count if left[] has a 
        // smaller or equal element
        if (left[i] <= right[j]) 
            arr[k++] = left[i++];
              // If right is smaller, then it is smaller than n1-i 
          // elements because left[] is sorted
        else {
            arr[k++] = right[j++];
            res += (n1 - i);
        }
    }
     // Merge remaining elements
    while (i < n1)
        arr[k++] = left[i++];
    while (j < n2)
        arr[k++] = right[j++];
     return res;
}
 // Function to count inversions in the array
int countInv(vector<int>& arr, int l, int r){
    int res = 0;
    if (l < r) {
        int m = (r + l) / 2;
         // Recursively count inversions in the left and 
        // right halves
        res += countInv(arr, l, m);
        res += countInv(arr, m + 1, r);
         // Count inversions such that greater element is in 
          // the left half and smaller in the right half
        res += countAndMerge(arr, l, m, r);
    }
    return res;
}
 int inversionCount(vector<int> &arr) {
      int n = arr.size();
      return countInv(arr, 0, n-1);
}
 void bfs(int c,vector<vector<int>>g ){
    queue<int> q; 
    q.push(c) ;
    while(!q.empty()){
        int a = q.front() ; q.pop();
        for(auto x : g[a]){
                    }
    }
}
 int power(int x, int y, int p)
{
     // Initialize answer
    int res = 1;
     // Check till the number becomes zero
    while (y > 0) {
         // If y is odd, multiply x with result
        if (y % 2 == 1)
            res = (res * x);
         // y = y/2
        y = y >> 1;
         // Change x to x^2
        x = (x * x);
    }
    return res % p;
}
 void cyes(bool b){
    if (b) cout<<"YES"<<endl ;
    else{
        cout<<"NO"<<endl;
    }
}
void dfs(int c, int p , vector<vector<int>> & g,vector<int>& depth){
    if (g[c].size()==1 && g[c][0]==p){
        depth[c] = 0 ;
        return ;
    }
    for (auto a : g[c]){
        if (a==p) continue;
        else{
            depth[c] = min(depth[a]+1,depth[c]) ;
        }
    }
}
   /*-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o- CODE BELOW -o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-*/
        void solve(int ii){
             take(n) ;
            Itarr(n) ;
            int ans = 0; 
            int first_occ[n+2] ; 
            set_tox(first_occ,n+2,-1)
             fwd(i,0,n){ 
                if ((arr[i] <= n) && (first_occ[arr[i]] ==-1)){
                    first_occ[arr[i]] = i ;
                }
            }
             int cnt_arr[n+2] ;
            set_tox(cnt_arr,n+2,0) ;
            fwd(i,0,n){
                if (arr[i] <= n ){
                    cnt_arr[arr[i]]++ ;
                }
            }
            int curr = n-1 ;
            vector<int> neee ;
            fwd(i,0,n){
                if (i==first_occ[0]){
                    neee.pb(0) ;
                }
                else{
                    if (arr[i]!=0){
                        neee.pb(arr[i]) ;
                    }
                }
            }
            if (cnt_arr[0]==0){
                cout<<n<<endl ;
                return ;
            }
            int mn = INF ; 
            int mex = 0 ;
            fwd(i,0,n+1){
                if (cnt_arr[i]==0){
                    mex = i ;
                    break ;
                }
            }
            ans = cnt_arr[0] -1 ; 
            fwd(i,0,first_occ[0]){
                mn = min(mn,neee[i]) ;
                if (neee[i] <=n) cnt_arr[neee[i]]-- ;
                if ((neee[i]<=mex-1 ) && (cnt_arr[neee[i]]==0)){
                    mex = neee[i] ; 
                }
                // what_is(mn)
                // what_is(mex)
                if (mn < mex){
                    ans++ ;
                    break ; 
                }
            }
               cout<<(n-ans)<<endl;
                                  }   
         int32_t main(){
            // freopen("input.txt",'r') ;
            // freopen("output.txt",'w') ;
            ios_base::sync_with_stdio(false) ; 
            cin.tie(NULL) ; cout.tie(NULL) ;
            cin>>tt ;
            // sieve() ; 
            int ii =0 ; 
            while(tt--){
                ii++ ; 
                solve(ii) ;
             }  
            return 0 ;                
            }