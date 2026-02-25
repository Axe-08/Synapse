#include <bits/stdc++.h>
#define rep(i,a,b) for(int i=a;i<b;i++)
#define rrep(i,a,b) for(int i=a;i>=b;i--)
#include <ext/pb_ds/assoc_container.hpp> // Common file
#include <ext/pb_ds/tree_policy.hpp>
#define irep rep(i,0,n)
#define int long long
#define pii pair<int,int>
#define si set<int>
#define in(a) int a;cin>>a;
#define nod(i) cout<<fixed<<setprecision(i)
#define take(a,n) int a[n]; for(int j=0;j<n;j++) cin>>a[j];
#define ssin string s; cin>>s;
using namespace std;
using namespace __gnu_pbds;
 typedef tree<int, null_type, less<int>, rb_tree_tag,tree_order_statistics_node_update> ordered_set;
typedef tree<pair<int, int>, null_type,less<pair<int, int> >, rb_tree_tag,tree_order_statistics_node_update> ordered_multiset;
  void solve()
{
    in(n)
    take(a,n)
    set<int> s;
    irep{s.insert(i);}
    int z=0;
    int mex=0;
    int ans=0;
    bool flag=true;
    rrep(i,n-1,0){
        // if(flag){
            if(a[i]==(*s.begin())){
                ans++;
                // s.erase(a[i]);
            }
            else{
                if(a[i]<(*s.begin())){
                    // flag=false;
                    ans=max(ans,n-i-z);
                }
                else{
                    ans++;
                }
            }
        // }
        // if(!flag){
        // }
        if(a[i]==0){z++;}
        s.erase(a[i]);
    }
    cout<<ans<<"\n";
}
signed main()
{
    ios_base::sync_with_stdio(0);
    cin.tie(0);
    cout.tie(0);
    int t=1;
    cin>>t;
    while(t--){
        solve();
    }
    return 0;
}