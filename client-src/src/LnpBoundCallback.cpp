// flags: -O2 -std:c++17 -GR-
// Reproduces the six virtual bodies of the callable at native vtable RVA157adfc.
// The creation site RVA2dc743 binds method RVA2e9d40 and ESI, with placeholder _1.
// The argument is opaque: its reference ABI is proved, its canonical type and
// cv qualification are not. The bound method body is not reconstructed here.
#define _HAS_STATIC_RTTI 0
#include <functional>
#include <utility>
struct CallbackArgument2e9d40;
struct CallbackContext2dc580
{
    void Method2e9d40(CallbackArgument2e9d40& argument);
};
using Binder2dc743 = decltype(std::bind(&CallbackContext2dc580::Method2e9d40,
    std::declval<CallbackContext2dc580*&>(), std::placeholders::_1));
template class std::_Func_impl_no_alloc<Binder2dc743, void, CallbackArgument2e9d40&>;

// Exact implementations; the opaque type records only the reference ABI.
// match: 2f2780 ?_Copy@?$_Func_impl_no_alloc@V?$_Binder@U_Unforced@std@@P8CallbackContext2dc580@@AEXAAUCallbackArgument2e9d40@@@ZAAPAU3@ABU?$_Ph@$00@2@@std@@XAAUCallbackArgument2e9d40@@@std@@EBEPAV?$_Func_base@XAAUCallbackArgument2e9d40@@@2@PAX@Z
// same: 2f2780 ?_Move@?$_Func_impl_no_alloc@V?$_Binder@U_Unforced@std@@P8CallbackContext2dc580@@AEXAAUCallbackArgument2e9d40@@@ZAAPAU3@ABU?$_Ph@$00@2@@std@@XAAUCallbackArgument2e9d40@@@std@@EAEPAV?$_Func_base@XAAUCallbackArgument2e9d40@@@2@PAX@Z
// match: 2f2a00 ?_Do_call@?$_Func_impl_no_alloc@V?$_Binder@U_Unforced@std@@P8CallbackContext2dc580@@AEXAAUCallbackArgument2e9d40@@@ZAAPAU3@ABU?$_Ph@$00@2@@std@@XAAUCallbackArgument2e9d40@@@std@@EAEXAAUCallbackArgument2e9d40@@@Z
// match: 125630 ?_Target_type@?$_Func_impl_no_alloc@V?$_Binder@U_Unforced@std@@P8CallbackContext2dc580@@AEXAAUCallbackArgument2e9d40@@@ZAAPAU3@ABU?$_Ph@$00@2@@std@@XAAUCallbackArgument2e9d40@@@std@@EBEABVtype_info@@XZ
// match: 2f27b0 ?_Delete_this@?$_Func_impl_no_alloc@V?$_Binder@U_Unforced@std@@P8CallbackContext2dc580@@AEXAAUCallbackArgument2e9d40@@@ZAAPAU3@ABU?$_Ph@$00@2@@std@@XAAUCallbackArgument2e9d40@@@std@@EAEX_N@Z
// same: 10aa40 ?_Get@?$_Func_impl_no_alloc@V?$_Binder@U_Unforced@std@@P8CallbackContext2dc580@@AEXAAUCallbackArgument2e9d40@@@ZAAPAU3@ABU?$_Ph@$00@2@@std@@XAAUCallbackArgument2e9d40@@@std@@EBEPBXXZ
