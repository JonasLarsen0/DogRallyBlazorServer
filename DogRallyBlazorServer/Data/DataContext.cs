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
            var faker = new Faker("en");

            for (int i = 1; i < 10; i++)
            {
                var track = new Track
                {
                    TrackId = i,
                    Date = faker.Date.Past(),
                    PlaceName = faker.Address.City(),
                    CreatorName = faker.Name.FullName(),
                    JudgeName = faker.Name.FullName(),
                    TrackImg = faker.Internet.Avatar(),
                    Class = GetRandomClass()
                };
                tracks.Add(track);
            }
            return tracks;
        }
        private Class GetRandomClass()
        {
            var random = new Random();
            var types = Enum.GetValues(typeof(Class));
            return (Class)types.GetValue(random.Next(types.Length));
        }
        
    }
}
