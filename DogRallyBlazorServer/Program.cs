using Microsoft.EntityFrameworkCore;
using Microsoft.AspNetCore.Identity;
using DogRallyBlazorServer.Data;
using DogRallyBlazorServer.Services;
using Syncfusion.Blazor;

var builder = WebApplication.CreateBuilder(args);

//Syncfusion license
Syncfusion.Licensing.SyncfusionLicenseProvider.RegisterLicense("MzI5MjExN0AzMjM1MmUzMDJlMzBnVDdQdTUxTFo2bHpVeFRwV1M5RC9yM0dVblZwOUlrWjkxeDg1eDhndGZNPQ==");

// Add services to the container.
builder.Services.AddRazorPages();
builder.Services.AddServerSideBlazor();
builder.Services.AddSyncfusionBlazor(); //Syncfusion functionality

builder.Services.AddScoped<ITrackService, TrackService>(); //Dependency injection for TrackService 

var connectionString = builder.Configuration.GetConnectionString("DefaultConnection"); //Creates access to database via the connection string
builder.Services.AddDbContextFactory<DataContext>(options => options.UseSqlServer(connectionString));

//Identity setting requirements.
builder.Services.AddIdentity<IdentityUser, IdentityRole>(options =>
{
    options.Password.RequireDigit = false;
    options.Password.RequiredLength = 5;
    options.Password.RequireLowercase = false;
    options.Password.RequireUppercase = false;
    options.Password.RequireNonAlphanumeric = false;
    options.SignIn.RequireConfirmedAccount = false;

}) .AddEntityFrameworkStores<DataContext>();

var app = builder.Build();

using (var scope = app.Services.CreateScope()) //using makes sure that the scope is disposed of after the block is executed
{
    var dbContext = scope.ServiceProvider.GetRequiredService<DataContext>();
    dbContext.Database.EnsureCreated();
}

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    // The default HSTS value is 30 days. You may want to change this for production scenarios, see https://aka.ms/aspnetcore-hsts.
    app.UseHsts();
}

app.UseHttpsRedirection();

app.UseStaticFiles();

app.UseRouting();

app.UseAuthentication();
app.UseAuthorization(); //needs to be after UseAuthentication because it relies on the user identity from the authentication process.

app.MapBlazorHub();
app.MapFallbackToPage("/_Host");

app.Run();
