using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using System.ComponentModel.DataAnnotations;

namespace DogRallyBlazorServer.Areas.Identity.Pages.Account
{
    public class LoginModel : PageModel
    {
        private readonly SignInManager<IdentityUser> _signInManager;

        public LoginModel(SignInManager<IdentityUser> signInManager)
        {
            _signInManager = signInManager;
        }

        [BindProperty]
        public InputModel Input { get; set; }

        public async Task<IActionResult> OnPostAsync()
        {
            if (ModelState.IsValid)
            {
                var result = await _signInManager.PasswordSignInAsync(Input.Email, Input.Password, isPersistent: false, lockoutOnFailure: false);

                if (result.Succeeded)
                {
                    return LocalRedirect("~/"); //redirects to the home page if the login is successful //index.razor
                }
            }

            return Page(); //fails returns the page
        }
    }

    public class InputModel
    {
        [Required]  //The Required attribute ensures that the user has to enter a value in the field.
        [EmailAddress]
        public string Email { get; set; }

        [Required]
        [DataType(DataType.Password)] //The DataType attribute password ensures that it is stored in a encrypted format. 
        public string Password { get; set; }
    }

}
