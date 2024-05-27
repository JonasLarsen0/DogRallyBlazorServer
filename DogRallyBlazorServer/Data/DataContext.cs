using Bogus;
using DogRallyBlazorServer.Models;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;

namespace DogRallyBlazorServer.Data
{
    public class DataContext: IdentityDbContext 
    {
        public DbSet<Track> Tracks { get; set; }
        public DataContext(DbContextOptions options) : base(options) { }

        protected override void OnModelCreating(ModelBuilder builder)
        {
            base.OnModelCreating(builder);

            builder.Entity<Track>().HasData(GetTracks());
        }

        private List<Track> GetTracks()
        {
            var tracks = new List<Track>();
            var faker = new Faker("en"); //Creating fake data for the database using Bogus nuget package.

            for (int i = 1; i < 10; i++)
            {
                var track = new Track
                {
                    TrackId = i,
                    Date = faker.Date.Past(),
                    PlaceName = faker.Address.City(),
                    CreatorName = faker.Name.FullName(),
                    JudgeName = faker.Name.FullName(),
                    RallyClass = GetRandomClass(),
                    FileName = faker.Internet.Avatar()
                };
                tracks.Add(track);
            }
            return tracks;
        }
        private RallyClass GetRandomClass() //Getting random enum value of the RallyClass.
        {
            var random = new Random();
            var types = Enum.GetValues(typeof(RallyClass));
            return (RallyClass)types.GetValue(random.Next(types.Length));
        }
        
    }
}
